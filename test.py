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

async def test_list_of_tools(params):
    print( "1. Test : list of tools ... ")
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_response = await session.list_tools()
            print("\n instruments:")
            for tool in tools_response.tools:
                print(f"- {tool.name}: {tool.description}")

async def test_get_tree(params):
    print( "2. Test : get_tree ...")
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            try:
                result = await session.call_tool("get_tree", arguments={})
                print(f"\n get_tree: {result}")
            except Exception as e:
                assert False, f"\n[FAILED]: {e}"

async def test_server(cmd, srv, port):
    print( "3. Test : remote server ...")
    local_env = os.environ.copy()
    local_env["BBMCPS_PORT"] = str(port)
    p = subprocess.Popen([cmd, srv], env=local_env)
    time.sleep(3)
    try:
        async with Client(f"http://127.0.0.1:{port}/mcp") as client:
            tools_response = await client.list_tools()
            for tool in tools_response.tools:
                print(f"{tool.name}: {tool.description}")
            echo_text = "TEST123"
            result = await client.call_tool(
                name="echo",
                arguments = {"text" : echo_text })
            print(f"echo: {str(result.content)}")
            assert echo_text in str(result.content)
    except Exception as e:
        assert False, f"\n[FAILED]: {e}"
    p.kill() #p.terminate()
    p.wait()

async def test_agent_profile(params):
    print( "4. Test : agent profile ...")
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            try:
                result = await session.call_tool(
                    "save_agent_profile",
                    arguments={
                        "name" : "coder",
                        "system_prompt" : "You are an senior coder."
                    }
                )
                print(f"\n result: {result}")
                assert not result.is_error
                # if hasattr(result, 'content') and result.content:
                #     print( str(result.content))
                result = await session.call_tool(
                    "get_agent_profile",
                    arguments={
                        "name" : "coder"
                    }
                )
                print(f"\n result: {result}")
                assert not result.is_error
            except Exception as e:
                assert False, f"\n[FAILED]: {e}"

async def test_note(params):
    print( "5. Test : note save ...")
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
                print(f"\n result: {result}")
                assert not result.is_error
            except Exception as e:
                assert False, f"\n[FAILED]: {e}"

async def tests(mcp_srv):
    cmdPython = "python3"
    params = StdioServerParameters(
        command=cmdPython,
        args=[mcp_srv]
    )
    print( "BBMCPS tests ...")
    await test_list_of_tools(params)
    await test_get_tree(params)
    await test_server(cmdPython, mcp_srv, 12345)
    await test_agent_profile(params)
    await test_note(params)

if __name__ == "__main__":
    if 2 == len(sys.argv):
        asyncio.run( tests(sys.argv[1]) )
    else:
        print("Usage: python3 path_to_bbmcps/test.py path_to_bbmcps")
        exit(1)

