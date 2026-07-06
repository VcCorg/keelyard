"""Test version command."""

from typer.testing import CliRunner

from agentic_cli import __version__
from agentic_cli.main import app

runner = CliRunner()


def test_version_command():
    """Test that --version displays the correct version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
    assert "keel-agentic-cli" in result.stdout


def test_version_short_flag():
    """Test that -v displays the correct version."""
    result = runner.invoke(app, ["-v"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_command():
    """Test that --help displays help information."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "KEEL Agentic CLI" in result.stdout


def test_hello_command():
    """Test the hello command."""
    result = runner.invoke(app, ["hello"])
    assert result.exit_code == 0
    assert "Hello" in result.stdout
    assert "World" in result.stdout


def test_hello_command_with_name():
    """Test the hello command with a custom name."""
    result = runner.invoke(app, ["hello", "KEEL"])
    assert result.exit_code == 0
    assert "Hello" in result.stdout
    assert "KEEL" in result.stdout
