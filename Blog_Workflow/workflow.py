from typing import Optional, List
import json
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.run.response import RunResponse, RunEvent
from agno.tools.firecrawl import FirecrawlTools
from agno.utils.log import logger
from agno.workflow import Workflow
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from Prompt import agents_config, tasks_config
from config import PostType
from schedule import schedule

load_dotenv()

class BlogAnalyzer(BaseModel):
    title: str
    blog_content_markdown: str

class Tweet(BaseModel):
    content: str
    is_hook: bool = Field(
        default = False,
        description = "Marks if this tweet is the 'hook' (first tweet)"
    )
    media_urls: Optional[List[str]] = Field(
        default_factory=list,
        description = "Associated media URLs, if any"
    )

class Thread(BaseModel):
    topic: str
    tweets: List[Tweet]

class LinkedInPost(BaseModel):
    content: str
    media_urls: Optional[List[str]] = None

class ContentPlanningWorkflow(Workflow):
    description: str = (
        "Plan, schedule, and publish social media content based on a blog post."
    )

    # Blog analyzer
    blog_analyzer: Agent = Agent(
        model = OpenAIChat(id = 'gpt-4o'),
        tools = [
            FirecrawlTools(scrape=True, crawl=False)
        ],
        description = f"{agents_config['blog_analyzer']['role']} - {agents_config['blog_analyzer']['goal']}",
        instructions=[
            f"{agents_config['blog_analyzer']['backstory']}",
            tasks_config['analyze_blog']
            ['description']
        ],

        response_model=BlogAnalyzer
    )


    # Twitter Thread Planner
    twitter_thread_planner: Agent = Agent(
        model = OpenAIChat(id = 'gpt-4o'),
        description = f"{agents_config['twitter_thread_planner']['role']} - {agents_config['twitter_thread_planner']['goal']}",
        instructions=[
            f"{agents_config['twitter_thread_planner']['backstory']}",
            tasks_config['create_twitter_thread_plan']['description'],
        ],
        response_model=Thread,
    )

    # LinkedInPostPlanner
    linkedin_post_planner: Agent = Agent(
        model = OpenAIChat(id = 'gpt-4o'),
        description= f"{agents_config['linkedin_post_planner']['role']} - {agents_config['linkedin_post_planner']['goal']}",
        instructions = [
            f"{agents_config['linkedin_post_planner']['backstory']}",
            tasks_config['create_linkedin_post_plan']['description'],
        ],
        response_model=LinkedInPost,
    )

    def scrape_blog_post(self, blog_post_url: str, use_cache: bool = True):
        if use_cache and blog_post_url in self.session_state:
            logger.info(f"Using cache from post post: {blog_post_url}")
            return self.session_state[blog_post_url]
        else:
            response: RunResponse = self.blog_analyzer.run(blog_post_url)
            if isinstance(response.content, BlogAnalyzer):
                result = response.content
                logger.info(f"Blog title: {result.title}")
                self.session_state[blog_post_url] = result.blog_content_markdown
                return result.blog_content_markdown
            else:
                raise ValueError("Unexpected content type received from blog analyzer")

    def generate_plan(self, blog_content: str, post_type: PostType):
        plan_response: RunResponse = RunResponse(content=None)
        if post_type == PostType.TWITTER:
            logger.info(f"Generating post plan for {post_type}")
            plan_response = self.twitter_thread_planner.run(blog_content)

        elif post_type == PostType.LINKEDIN:
            logger.info(f"Generating post plan for {post_type}")
            plan_response = self.linkedin_post_planner.run(blog_content)
        else:
            raise ValueError("Unexpected post type received from blog analyzer")

        # Plan has a response
        if isinstance(plan_response.content, (Thread, LinkedInPost)):
            return plan_response.content
        elif isinstance(plan_response.content, str):
            data = json.loads(plan_response.content)
            if post_type == PostType.TWITTER:
                return Thread(**data)
            else:
                return LinkedInPost(**data)
        else:
            raise ValueError("Unexpected post type received from blog analyzer")


    def schedule_and_publish(self, plan, post_type: PostType) -> RunResponse:
        logger.info(f"Publishing content for {post_type}")
        response = schedule(
            thread_model = plan,
            post_type = post_type,
        )

        logger.info(f"Response from schedule: {response}")

        if response:
            return RunResponse(content=response, event=RunEvent.workflow_completed)
        else:
            return RunResponse(content='Failed to schedule content.', event=RunEvent.workflow_completed)


    def run(self, blog_post_url, post_type) -> RunResponse:
        blog_content = self.scrape_blog_post(blog_post_url)

        plan = self.generate_plan(blog_content, post_type)

        response = self.schedule_and_publish(plan, post_type)

        return response



if __name__ == "__main__":
    blogpost_url = "https://cp-algorithms.com/data_structures/sparse-table.html"
    workflow = ContentPlanningWorkflow()
    post_response = workflow.run(
        blog_post_url = blogpost_url,
        post_type = PostType.LINKEDIN
    )
    logger.info(post_response.content)



