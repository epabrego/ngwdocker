from pathlib import Path
import click

from .context import Context


@click.command()
@click.option('-c', '--config', type=click.Path(exists=True, dir_okay=False, file_okay=True))
def main(config=None):
    config_path = Path('ngwdocker.yaml' if config is None else config)
    bctx = Context.from_file(config_path)
    bctx.load_packages()
    bctx.initialize()
