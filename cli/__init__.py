import click
import subprocess


@click.group()
@click.version_option(version="2.4.2")
@click.pass_context
def cli(ctx):
    pass


@click.command()
@click.option("--run-streamlit", is_flag=True, help="Run the Streamlit app.")
@click.option("-p", "--port", type=int, default=8501, help="Streamlit port")
def run_streamlit(run_streamlit, port):
    """Run the Streamlit app."""
    subprocess.run(
        ["streamlit", "run", "interface/streamlit_app.py", "--server.port", str(port)]
    )


cli.add_command(run_streamlit)
