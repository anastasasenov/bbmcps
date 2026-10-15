# BBMCPS TESTS

import os
import sys
import json
import asyncio
import time
import subprocess
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import Client

async def call_tool(session, tool, args):
    result = await session.call_tool(tool, args)
    assert not result.is_error
    print(f"\t{tool} ... OK")
    return result

async def test_list_of_tools(num, params):
    print( f"\n{num}. Test list of tools ... ")
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_response = await session.list_tools()
            assert 23 == len(tools_response.tools)
            print(f"\t{len(tools_response.tools)} instruments")
            for tool in tools_response.tools:
                assert len(tool.name) > 0
                assert len(tool.description) > 0

async def test_get_tree(num, params):
    print( f"\n{num}. Test simple tool - get_tree ...")
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            try:
                result = await call_tool( session, "get_tree",{})
            except Exception as e:
                assert False, f"\n[FAILED]: {e}"

async def test_server(num, cmd, srv, port):
    print( f"\n{num}. Test remote server ( tool echo ) ...")
    local_env = os.environ.copy()
    local_env["BBMCPS_PORT"] = str(port)
    p = subprocess.Popen([cmd, srv], env=local_env)
    time.sleep(3)
    try:
        async with Client(f"http://127.0.0.1:{port}/mcp") as client:
            tools_response = await client.list_tools()
            bHasEcho = False
            for tool in tools_response.tools:
                if tool.name == "echo":
                    bHasEcho = True
                    break
            assert bHasEcho
            echo_text = "TEST123"
            result = await client.call_tool(
                name="echo",
                arguments = {"text" : echo_text })
            assert echo_text in str(result.content)
            print("\techo ... OK")
    except Exception as e:
        assert False, f"\n[FAILED]: {e}"
    p.kill() #p.terminate()
    p.wait()

async def test_agent_profile(num, params):
    print( f"\n{num}. Test agent profiles ...")
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            try:
                result = await call_tool(
                    session,
                    "save_agent_profile",
                    {
                        "name" : "coder",
                        "system_prompt" : "You are an senior coder."
                    }
                )
                result = await call_tool(
                    session,
                    "get_agent_profile",
                    {
                        "name" : "coder"
                    }
                )
                data = json.loads(result.content[0].text)
                assert data['profile']["name"] == "coder"
            except Exception as e:
                assert False, f"\n[FAILED]: {e}"

async def test_note(num, params):
    print( f"\n{num}. Test : note save/delete ...")
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            try:
                result = await session.call_tool(
                    "save_note",
                    arguments={
                        "topic" : "C++",
                        "content" : "This is crazy language.",
                        "category" : "programming"
                    }
                )
                print(f"\n save_note result: {result}")
                assert not result.is_error
                result = await session.call_tool(
                    "get_note",
                    arguments={
                        "topic" : "C++"
                    }
                )
                print(f"\n get_note result: {result}")
                assert not result.is_error
                result = await session.call_tool(
                    "delete_note",
                    arguments={
                        "topic" : "C++"
                    }
                )
                print(f"\n delete_note result: {result}")
                assert not result.is_error
            except Exception as e:
                assert False, f"\n[FAILED]: {e}"

async def test_search(num, params):
    print( f"\n{num}. Test : search ...")
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            try:
                result = await session.call_tool(
                    "save_note",
                    arguments={
                        "topic" : "Python",
                        "content" : "It is the best language.",
                        "category" : "programming"
                    }
                )
                print(f"\n save_note result: {result}")
                assert not result.is_error
                result = await session.call_tool(
                    "save_note",
                    arguments={
                        "topic" : "jscript",
                        "content" : "I like this language.",
                        "category" : "programming"
                    }
                )
                print(f"\n save_note result: {result}")
                assert not result.is_error
                result = await session.call_tool(
                    "search_notes",
                    arguments={
                        "category" : "programming",
                        "query" : "language"
                    }
                )
                print(f"\n search_notes result: {result}")
                assert not result.is_error
                data = json.loads(result.content[0].text)
                assert 2 == data["count"]
            except Exception as e:
                assert False, f"\n[FAILED]: {e}"

async def tests(mcp_srv):
    cmdPython = "python3"
    params = StdioServerParameters(
        command=cmdPython,
        args=[mcp_srv]
    )
    print( "BBMCPS tests ...")
    await test_list_of_tools(1, params)
    await test_get_tree(2, params)
    await test_agent_profile(3, params)
    await test_note(4, params)
    await test_search(5, params)
    await test_server(6, cmdPython, mcp_srv, 12345)

if __name__ == "__main__":
    if 2 == len(sys.argv):
        asyncio.run( tests(sys.argv[1]) )
    else:
        print("Usage: python3 path_to_bbmcps/test.py path_to_bbmcps")
        exit(1)

