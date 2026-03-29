import logging
from livekit import agents
from aigita_agent import create_agent

logging.basicConfig(level=logging.INFO)

app = agents.WorkerOptions(
    entrypoint_fnc=create_agent,
)

if __name__ == "__main__":
    agents.cli.run_app(app)
