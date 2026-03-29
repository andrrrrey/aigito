import logging
from livekit.agents import WorkerOptions, cli
from aigita_agent import create_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=create_agent))
