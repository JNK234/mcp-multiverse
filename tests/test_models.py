# Tests for core data models
import pytest

from mcpx.models import Config, MCPServer


def test_mcp_server_creation():
    """Test creating MCPServer instances."""
    server = MCPServer(
        name="test",
        command="npx",
        args=["-y", "server"],
        env={"KEY": "value"},
    )
    assert server.name == "test"
    assert server.command == "npx"
    assert server.args == ["-y", "server"]
    assert server.env == {"KEY": "value"}


def test_mcp_server_defaults():
    """Test MCPServer with default values."""
    server = MCPServer(name="test", command="echo")
    assert server.args == []
    assert server.env == {}


def test_mcp_server_immutability():
    """Test that MCPServer is frozen (immutable)."""
    server = MCPServer(name="test", command="echo")
    with pytest.raises(AttributeError):
        server.name = "new_name"
    with pytest.raises(AttributeError):
        server.command = "new_command"


def test_mcp_server_equality():
    """Test MCPServer equality comparison."""
    server1 = MCPServer(name="test", command="echo")
    server2 = MCPServer(name="test", command="echo")
    server3 = MCPServer(name="test", command="npx")

    assert server1 == server2
    assert server1 != server3


def test_config_creation():
    """Test creating Config instances."""
    server1 = MCPServer(name="test1", command="echo")
    server2 = MCPServer(name="test2", command="npx")

    config = Config(
        version="1.0",
        servers={"test1": server1, "test2": server2},
    )

    assert config.version == "1.0"
    assert len(config.servers) == 2
    assert config.servers["test1"] == server1
    assert config.servers["test2"] == server2


def test_config_mutability():
    """Test that Config is mutable (not frozen)."""
    server = MCPServer(name="test", command="echo")
    config = Config(version="1.0", servers={"test": server})

    # Should be able to modify
    config.version = "2.0"
    config.servers["new"] = MCPServer(name="new", command="test")

    assert config.version == "2.0"
    assert len(config.servers) == 2
