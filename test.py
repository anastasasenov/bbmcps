# BBMCPS TESTS

import os
import sys
import json
import asyncio
import time
import subprocess
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import Client

async def call_tool(session, tool, args):
    result = None
    try:
        result = await session.call_tool(tool, args)
        assert not result.is_error
        print(f"\t{tool} ... OK")
    except Exception as e:
        assert False, f"\n\t[FAILED]: {e}\n\t\t{tool}({str(args)})"
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
            await call_tool( session, "get_tree",{})

async def test_server(num, cmd, srv, port):
    print( f"\n{num}. Test remote server ( tool echo ) ...")
    if "BBMCPS_DEBUG" in os.environ:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
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

async def test_note(num, params):
    print( f"\n{num}. Test : note save/delete ...")
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await call_tool(
                session,
                "save_note",
                {
                    "topic" : "C++",
                    "content" : "There are no seatbelts in C++.",
                    "category" : "programming"
                }
            )
            result = await call_tool(
                session,
                "get_note",
                { "topic" : "C++" }
            )
            data = json.loads(result.content[0].text)
            assert data["note"]['category'] == "programming"
            result = await call_tool(
                session,
                "delete_note",
                { "topic" : "C++" }
            )

async def test_search(num, params):
    print( f"\n{num}. Test : search ...")
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await call_tool(
                session,
                "save_note",
                {
                    "topic" : "Python",
                    "content" : "It is the best language.",
                    "category" : "programming"
                }
            )
            result = await call_tool(
                session,
                "save_note",
                {
                    "topic" : "jscript",
                    "content" : "I like this language.",
                    "category" : "programming"
                }
            )
            result = await call_tool(
                session,
                "search_notes",
                {
                    "category" : "programming",
                    "query" : "language"
                }
            )
            data = json.loads(result.content[0].text)
            assert 2 == data["count"]

async def test_resources(num, params):
    print( f"\n{num}. Test resources ...")
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_resources()
            print(f"\t{len(result.resources)} resources")
            assert 5 == len(result.resources)
            for res in result.resources:
                assert len(res.name) > 0
                assert len(res.uri) > 0
                assert len(res.description) > 0
                #print(f"\t {res.name} {res.uri} {res.description}")

async def tests(mcp_srv):
    cmdPython = "python3"
    params = StdioServerParameters(
        command=cmdPython,
        args=[mcp_srv]
    )
    print( "BBMCPS tests ...")
    await test_list_of_tools(1, params)
    await test_resources(2, params)
    await test_get_tree(3, params)
    await test_agent_profile(4, params)
    await test_note(5, params)
    await test_search(6, params)
    await test_server(7, cmdPython, mcp_srv, 12345)

if __name__ == "__main__":
    if 2 == len(sys.argv):
        asyncio.run( tests(sys.argv[1]) )
    else:
        print("Usage: python3 path_to_bbmcps/test.py path_to_bbmcps")
        exit(1)

