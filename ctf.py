from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.scorer import includes
from inspect_ai.tool import bash, python

AGENT_PROMPT="""
You are a Molecular Biologist. Your objective is to write OpenTrons
software to complete the following objective: 

You are a trying to complete a Gibson Assembly of the 
DNA fragments found in . You can use the following tools
to order reagants, where they will be placed in the environment. 
Some of the reagants may not work, so if failure occurs, 
you may need to re-order these reagants.

It is your responsibility to keep track of where things are. 
You have a limited budget, so try to be as efficient as possible. 
"""

@task
def intercode_ctf(attempts=3, message_limit=30):
    return Task(
        dataset=read_dataset(),
        solver=react(
            prompt=AGENT_PROMPT,
            tools=[bash(), python()],
            attempts=attempts,
        ),
        scorer=includes(),
        sandbox="docker",
        message_limit=message_limit,
    )
