# BBMCPS TESTS

import os
import sys
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_list_of_tools(params):
    print( "Test : list of tools")
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_response = await session.list_tools()
            print("\n instruments:")
            for tool in tools_response.tools:
                print(f"- {tool.name}: {tool.description}")

async def tests(mcp_srv):
    params = StdioServerParameters(
        command="python3",
        args=[mcp_srv]
    )
    print( "BBMCPS tests ...")
    os.environ["BBMCPS_SERVER_STDIO"] = "stdio"
    await test_list_of_tools(params)

if __name__ == "__main__":
    if 2 == len(sys.argv):
        asyncio.run( tests(sys.argv[1]) )
    else:
        print("Usage: python3 path_to_bbmcps/test.py path_to_bbmcps")
        exit(1)

