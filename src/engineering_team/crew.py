from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel, Field
import os


class CodeOutput(BaseModel):
    code: str = Field(description="The full Python source code.")
    description: str = Field(description="A brief description of what the code does.")



@CrewBase
class EngineeringTeam():
    """EngineeringTeam crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self, task_callback=None, step_callback=None):
        self.task_callback = task_callback
        self.step_callback = step_callback
        
        # Initialize LLMs with explicit max_tokens to prevent OpenRouter credit/limit errors
        # Using 4000 tokens as a safe upper bound for complex engineering tasks
        self.lead_llm = LLM(
            model=os.getenv("LEAD_MODEL", "openrouter/openai/gpt-4o"),
            max_tokens=4000
        )
        self.engineer_llm = LLM(
            model=os.getenv("ENGINEER_MODEL", "openrouter/anthropic/claude-3.7-sonnet"),
            max_tokens=4000
        )
        self.writer_llm = LLM(
            model=os.getenv("WRITER_MODEL", "openrouter/google/gemini-2.0-flash-001"),
            max_tokens=4000
        )

    @agent
    def engineering_lead(self) -> Agent:
        return Agent(
            config=self.agents_config['engineering_lead'],
            llm=self.lead_llm,
            verbose=True,
            allow_code_execution=False
        )

    @agent
    def backend_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['backend_engineer'],
            llm=self.engineer_llm,
            verbose=True,
            allow_code_execution=False,
            max_execution_time=500, 
            max_retry_limit=3 
        )
    
    @agent
    def frontend_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['frontend_engineer'],
            llm=self.engineer_llm,
            verbose=True,
            allow_code_execution=False
        )
    
    @agent
    def test_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['test_engineer'],
            llm=self.engineer_llm,
            verbose=True,
            allow_code_execution=False,
            max_execution_time=500, 
            max_retry_limit=3 
        )

    @agent
    def documentation_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['documentation_engineer'],
            llm=self.writer_llm,
            verbose=True,
            allow_code_execution=False
        )

    @task
    def design_task(self) -> Task:
        return Task(
            config=self.tasks_config['design_task']
        )

    @task
    def code_task(self) -> Task:
        return Task(
            config=self.tasks_config['code_task'],
            output_pydantic=CodeOutput
        )

    @task
    def frontend_task(self) -> Task:
        return Task(
            config=self.tasks_config['frontend_task'],
            output_pydantic=CodeOutput
        )

    @task
    def test_task(self) -> Task:
        return Task(
            config=self.tasks_config['test_task'],
            output_pydantic=CodeOutput
        )   

    @task
    def documentation_task(self) -> Task:
        return Task(
            config=self.tasks_config['documentation_task'],
        )

    @task
    def requirements_task(self) -> Task:
        return Task(
            config=self.tasks_config['requirements_task'],
            output_pydantic=CodeOutput
        )

    @crew
    def crew(self) -> Crew:
        """Creates the research crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            task_callback=self.task_callback,
            step_callback=self.step_callback,
        )