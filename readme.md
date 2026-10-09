## Blackboard MCP Server
![AI Assisted](https://shields.io)

This is an experimental MCP Server that provides an LLM with a persistent, structured memory and knowledge-management layer.

### Architecture

    Resource Layer - Tool Layer - Validation - Knowledge Graph - Transaction Layer - sqlite

### API

    RESOURCES

        blackboard://tree
        blackboard://agent-profiles
        blackboard://stats
        blackboard://recent
        blackboard://threads


    TOOLS

        save_note
        get_note
        delete_note
        search_notes

        get_ancestors
        get_descendants
        traverse_notes

        link_notes
        unlink_notes

        add_external_link
        remove_external_link

        save_agent_profile
        get_agent_profile
        list_agent_profiles
        delete_agent_profile

        create_thread
        post_comment
        get_thread
        list_threads
        update_thread_status

        get_statistics
        get_tree

### Database Schema

    The database consists of the following principal tables:
    
        agent_profiles -> notes -> external_links, note_relations
        
        topics_threads -> discussions

### Prerequisites

$ pip install mcp

### Inspired by

Shared Memory MCP Server ( https://github.com/dx-corp/shared-memory-mcp )

### License

This project is open-source and available under the MIT License.
