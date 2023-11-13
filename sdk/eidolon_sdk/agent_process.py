from __future__ import annotations

import asyncio
import importlib
import inspect
import typing
from typing import Optional, Annotated

from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo

from eidolon_sdk.util.dynamic_endpoint import add_dynamic_route
from .agent import Agent
from .agent_os import AgentOS
from .agent_program import AgentProgram


class ProcessResponse(BaseModel):
    process_id: str = Field(..., description="The ID of the conversation.")


class AgentProcess:
    agent: Agent
    agent_program: AgentProgram
    agent_os: AgentOS

    def __init__(self, agent_program: AgentProgram, agent_os: AgentOS):
        self.agent_program = agent_program
        self.agent_os = agent_os

    def start(self, app: FastAPI):
        # First create the Agent implementation
        module_name, class_name = self.agent_program.implementation.rsplit(".", 1)
        module = importlib.import_module(module_name)
        impl_class = getattr(module, class_name)

        self.agent = impl_class(self)

        add_dynamic_route(
            app=app,
            path=f"/{self.agent_program.name}",
            input_model=self.create_input_model(self.agent_program.initial_state),
            response_model=ProcessResponse,
            fn=self.processRoute(self.agent_program.initial_state),
            status_code=202,
        )

        for state_name, handler in self.agent.handlers.items():
            # the endpoint to hit to process/continue the current state
            add_dynamic_route(
                app=app,
                path=f"/{self.agent_program.name}/{{process_id}}/{state_name}",
                input_model=self.create_input_model(state_name),
                response_model=ProcessResponse,
                fn=self.processRoute(state_name),
                status_code=202,
            )

            # the endpoint to hit to retrieve the results after transitioning to the next state
            if handler.state_representation:
                app.add_api_route(
                    f"/{self.agent_program.name}/{{process_id}}/{state_name}",
                    endpoint=lambda *args, **kwargs: (asyncio.sleep(0)),
                    # todo, hook up state retrieval once memory is implemented
                    methods=["GET"],
                    response_model=handler.state_representation
                )

    def create_input_model(self, state_name):
        sig = inspect.signature(self.agent.handlers[state_name].fn).parameters
        hints = typing.get_type_hints(self.agent.handlers[state_name].fn, include_extras=True)
        fields = {}
        for param, hint in filter(lambda tu: tu[0] != 'return', hints.items()):
            if hasattr(hint, '__metadata__') and isinstance(hint.__metadata__[0], FieldInfo):
                field: FieldInfo = hint.__metadata__[0]
                field.default = sig[param].default
                fields[param] = (hint.__origin__, field)
            else:
                # _empty default isn't being handled by create_model properly (still optional when it should be required)
                default = ... if getattr(sig[param].default, "__name__", None) == '_empty' else sig[param].default
                fields[param] = (hint, default)

        input_model = create_model(f'{state_name.capitalize()}InputModel', **fields)
        return input_model

    def stop(self, app: FastAPI):
        pass

    def restart(self, app: FastAPI):
        self.stop(app)
        self.start(app)

    def processRoute(self, state: str):
        async def processStateRoute(request: Request, body: BaseModel, process_id: typing.Optional[str], background_tasks: BackgroundTasks):
            print(state)
            print(body)
            pid = process_id or self.agent_os.startProcess(request.headers.get('callback_url'))
            background_tasks.add_task(self.agent.base_handler, state=state, body=body)
            return {"process_id": pid}

        return processStateRoute

    def create_response_model(self, state: str):
        fields = {
            "conversation_id": (str, Field(..., description="The ID of the conversation.")),
        }
        for t_name, t_model in self.agent_program.states[state].transitions_to_models.items():
            fields[t_name] = (Optional[t_model], Field(default=None, description="The answer for {t_name} transition state."))

        return create_model(f'{state.capitalize()}ResponseModel', **fields)


class ConversationResponse(BaseModel):
    process_id: str = Field(..., description="The ID of the conversation.")