#!/usr/bin/env python3
"""
Heretto Deploy MCP Server - Complete Version with All Features
"""
import os
import sys
import json
import asyncio
import re
from typing import Any, Optional, List, Dict, Tuple

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from .client import HerettoDeployAPI


# Initialize API client (will use HERETTO_DEPLOY_TOKEN from env)
api_client = HerettoDeployAPI()

# Create server instance
server = Server("heretto-deploy-mcp")

# Get default values from environment
DEFAULT_ORG_ID = os.getenv("HERETTO_DEFAULT_ORG_ID")
DEFAULT_DEPLOYMENT_ID = os.getenv("HERETTO_DEFAULT_DEPLOYMENT_ID")
PORTAL_BASE_URL = os.getenv("HERETTO_PORTAL_BASE_URL", "").rstrip("/")


# ========== URL GENERATION HELPERS ==========
def add_urls_to_response(data: Any, depth: int = 0) -> Any:
    """Add portal URLs to paths in the response data."""
    if not PORTAL_BASE_URL:
        if depth == 0:  # Only log once
            print(f"Warning: PORTAL_BASE_URL not set, skipping URL generation", file=sys.stderr)
        return data
    
    if depth == 0:  # Only log at top level
        print(f"Adding URLs with base: {PORTAL_BASE_URL}", file=sys.stderr)
    
    # Handle different response types
    if isinstance(data, dict):
        # Make a copy to avoid modifying the original
        data = dict(data)  # Shallow copy
        
        # List of possible path field names
        path_fields = ["path", "href", "url", "link", "uri", "pathname"]
        
        for field in path_fields:
            if field in data and isinstance(data[field], str):
                # Check if it looks like a path (starts with /)
                if data[field].startswith("/"):
                    data["portal_url"] = f"{PORTAL_BASE_URL}{data[field]}"
                    print(f"Added URL from {field}: {data['portal_url']}", file=sys.stderr)
                # Check if it's a relative path without leading /
                elif data[field] and not data[field].startswith("http"):
                    data["portal_url"] = f"{PORTAL_BASE_URL}/{data[field]}"
                    print(f"Added URL from {field}: {data['portal_url']}", file=sys.stderr)
                break  # Only use the first matching field
        
        # For search results - handle various possible structures
        result_fields = ["results", "items", "data", "entries", "documents"]
        for field in result_fields:
            if field in data and isinstance(data[field], list):
                data[field] = [add_urls_to_response(item, depth + 1) for item in data[field]]
        
        # For structure/navigation items
        if "children" in data and isinstance(data["children"], list):
            data["children"] = [add_urls_to_response(child, depth + 1) for child in data["children"]]
        
        # Recursively process nested dictionaries (but skip certain fields)
        skip_fields = ["portal_url", "content", "body", "html"]
        for key, value in data.items():
            if key not in skip_fields and isinstance(value, (dict, list)):
                data[key] = add_urls_to_response(value, depth + 1)
    
    elif isinstance(data, list):
        # Process each item in the list
        return [add_urls_to_response(item, depth + 1) for item in data]
    
    return data


def format_response_with_prominent_urls(data: Any) -> Any:
    """Format responses to make URLs prominent and always visible."""
    if not PORTAL_BASE_URL or not isinstance(data, dict):
        return data
    
    # For search results, add a formatted section with links
    if "results" in data and isinstance(data["results"], list):
        # Create a links section at the top level
        data["quick_links"] = []
        for idx, result in enumerate(data["results"]):
            if "portal_url" in result:
                link_info = {
                    "title": result.get("title", f"Result {idx+1}"),
                    "url": result["portal_url"],
                    "description": result.get("description", "")[:100] + "..." if result.get("description") else ""
                }
                data["quick_links"].append(link_info)
    
    # For single content, add formatted link at top
    if "portal_url" in data and "content" in data:
        data["direct_link"] = {
            "title": data.get("title", "Document"),
            "url": data["portal_url"],
            "message": f"📄 View this document online: {data['portal_url']}"
        }
    
    return data


# ========== SMART SNIPPET EXTRACTION ==========
def extract_smart_snippet(content: str, query: str, max_length: int = 300) -> Dict:
    """Extract the most relevant snippet from content based on the query."""
    if not content:
        return {"snippet": "", "relevance_score": 0.0, "highlighted": False}
    
    # Normalize query and content
    query_lower = query.lower()
    query_terms = query_lower.split()
    
    # Split content into sentences
    sentences = re.split(r'(?<=[.!?])\s+', content)
    
    # Score each sentence based on query term matches
    sentence_scores = []
    for i, sentence in enumerate(sentences):
        sentence_lower = sentence.lower()
        score = sum(1 for term in query_terms if term in sentence_lower)
        
        # Bonus for exact phrase match
        if query_lower in sentence_lower:
            score += len(query_terms)
        
        # Bonus for sentences with multiple terms close together
        if score > 1:
            score *= 1.5
            
        sentence_scores.append((i, score, sentence))
    
    # Find the best sentence
    sentence_scores.sort(key=lambda x: x[1], reverse=True)
    
    if not sentence_scores or sentence_scores[0][1] == 0:
        # No matches found, return first paragraph
        return {
            "snippet": content[:max_length] + "..." if len(content) > max_length else content,
            "relevance_score": 0.0,
            "highlighted": False
        }
    
    # Get the best sentence and its context
    best_idx, best_score, best_sentence = sentence_scores[0]
    
    # Include surrounding sentences for context
    start_idx = max(0, best_idx - 1)
    end_idx = min(len(sentences), best_idx + 2)
    
    context_sentences = sentences[start_idx:end_idx]
    snippet = " ".join(context_sentences)
    
    # Highlight matching terms
    for term in query_terms:
        # Case-insensitive replacement with highlighting
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        snippet = pattern.sub(f"**{term}**", snippet)
    
    # Trim to max length if needed
    if len(snippet) > max_length:
        snippet = snippet[:max_length].rsplit(' ', 1)[0] + "..."
    
    return {
        "snippet": snippet,
        "relevance_score": min(1.0, best_score / len(query_terms)),
        "highlighted": True,
        "matched_terms": [term for term in query_terms if term in best_sentence.lower()]
    }


# ========== RELATED CONTENT SUGGESTIONS ==========
def get_related_content(current_path: str, all_results: List[Dict]) -> Dict:
    """Find related documentation based on the current path."""
    if not current_path:
        return {"related": []}
    
    # Extract path components
    path_parts = current_path.strip("/").split("/")
    current_section = path_parts[0] if path_parts else ""
    
    related = {
        "same_section": [],
        "parent_topics": [],
        "child_topics": [],
        "see_also": []
    }
    
    for result in all_results:
        if result.get("path") == current_path:
            continue  # Skip the current document
            
        result_path = result.get("path", "")
        result_parts = result_path.strip("/").split("/")
        
        # Same section (sibling documents)
        if result_parts and result_parts[0] == current_section:
            related["same_section"].append({
                "title": result.get("title", ""),
                "path": result_path,
                "portal_url": result.get("portal_url", "")
            })
        
        # Parent topic (shorter path in same hierarchy)
        elif result_path and current_path.startswith(result_path):
            related["parent_topics"].append({
                "title": result.get("title", ""),
                "path": result_path,
                "portal_url": result.get("portal_url", "")
            })
        
        # Child topic (longer path in same hierarchy)
        elif result_path.startswith(current_path):
            related["child_topics"].append({
                "title": result.get("title", ""),
                "path": result_path,
                "portal_url": result.get("portal_url", "")
            })
    
    # Limit results
    for key in related:
        related[key] = related[key][:3]
    
    return related


# ========== QUICK ANSWER EXTRACTION ==========
def extract_quick_answer(content: str, query: str) -> Optional[str]:
    """Try to extract a one-line answer for simple questions."""
    if not content:
        return None
    
    query_lower = query.lower()
    
    # Pattern matching for common question types
    patterns = {
        # What is X?
        r"what\s+is\s+(\w+)": r"(?i)(\w+)\s+is\s+([^.]+)\.",
        # How to X?
        r"how\s+to\s+(.+)": r"(?i)to\s+\1[^,]*,\s*([^.]+)\.",
        # What's the X?
        r"what'?s?\s+the\s+(\w+)": r"(?i)the\s+\1\s+is\s+([^.]+)\.",
        # Numbers/limits
        r"(limit|maximum|minimum|rate|cost|price)": r"(?i)(limit|maximum|minimum|rate|cost|price)[^:]*:\s*([^.\n]+)"
    }
    
    for question_pattern, answer_pattern in patterns.items():
        if re.search(question_pattern, query_lower):
            matches = re.findall(answer_pattern, content)
            if matches:
                # Return the first match, cleaned up
                answer = matches[0] if isinstance(matches[0], str) else matches[0][-1]
                return answer.strip()
    
    # Look for definitions (X: Y format)
    if "what" in query_lower or "define" in query_lower:
        # Extract the key term from the query
        terms = re.findall(r'\b(?!what|is|the|a|an)\w{3,}\b', query_lower)
        if terms:
            key_term = terms[0]
            # Look for "Term: definition" pattern
            pattern = rf"(?i){key_term}[^:]*:\s*([^.\n]+)"
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()
    
    return None


# ========== LEARNING PATH GENERATOR ==========
def generate_learning_path(current_topic: str, deployment_structure: Dict) -> List[Dict]:
    """Generate a suggested learning path based on the current topic."""
    # Map of topics to learning paths
    learning_paths = {
        "getting-started": [
            {"step": 1, "title": "Overview", "path": "/overview"},
            {"step": 2, "title": "Installation", "path": "/installation"},
            {"step": 3, "title": "Configuration", "path": "/configuration"},
            {"step": 4, "title": "First Steps", "path": "/first-steps"},
            {"step": 5, "title": "Best Practices", "path": "/best-practices"}
        ],
        "api": [
            {"step": 1, "title": "API Overview", "path": "/api/overview"},
            {"step": 2, "title": "Authentication", "path": "/api/authentication"},
            {"step": 3, "title": "Making Requests", "path": "/api/requests"},
            {"step": 4, "title": "Response Handling", "path": "/api/responses"},
            {"step": 5, "title": "Error Handling", "path": "/api/errors"}
        ],
        "troubleshooting": [
            {"step": 1, "title": "Common Issues", "path": "/troubleshooting/common"},
            {"step": 2, "title": "Error Messages", "path": "/troubleshooting/errors"},
            {"step": 3, "title": "Debugging Steps", "path": "/troubleshooting/debugging"},
            {"step": 4, "title": "Getting Help", "path": "/support"}
        ]
    }
    
    # Find matching learning path
    topic_lower = current_topic.lower()
    for key, path in learning_paths.items():
        if key in topic_lower:
            return path
    
    # Default learning path
    return [
        {"step": 1, "title": "Start Here", "path": "/"},
        {"step": 2, "title": "Core Concepts", "path": "/concepts"},
        {"step": 3, "title": "Practical Guides", "path": "/guides"},
        {"step": 4, "title": "Reference", "path": "/reference"}
    ]


# ========== ENHANCED SEARCH PROCESSING ==========
def enhance_search_results(results: List[Dict], query: str) -> Dict:
    """Enhance search results with all our killer features."""
    enhanced = {
        "query": query,
        "total_results": len(results),
        "enhanced_results": [],
        "quick_answer": None,
        "suggested_queries": [],
        "categories": {}
    }
    
    # Categorize results
    categories = {
        "guides": [],
        "api": [],
        "troubleshooting": [],
        "reference": [],
        "concepts": []
    }
    
    for idx, result in enumerate(results[:10]):  # Process top 10 results
        # Extract smart snippet if content is available
        snippet_data = None
        if "content" in result:
            snippet_data = extract_smart_snippet(result.get("content", ""), query)
            
            # Try to extract quick answer from first result
            if idx == 0 and not enhanced["quick_answer"]:
                quick = extract_quick_answer(result.get("content", ""), query)
                if quick:
                    enhanced["quick_answer"] = quick
        
        # Enhanced result
        enhanced_result = {
            **result,  # Keep all original fields
            "relevance_score": snippet_data["relevance_score"] if snippet_data else 0.5,
            "smart_snippet": snippet_data["snippet"] if snippet_data else result.get("description", ""),
            "highlighted_terms": snippet_data.get("matched_terms", []) if snippet_data else []
        }
        
        enhanced["enhanced_results"].append(enhanced_result)
        
        # Categorize
        path = result.get("path", "").lower()
        if "guide" in path or "how-to" in path:
            categories["guides"].append(enhanced_result)
        elif "api" in path:
            categories["api"].append(enhanced_result)
        elif "troubleshoot" in path or "error" in path:
            categories["troubleshooting"].append(enhanced_result)
        elif "reference" in path:
            categories["reference"].append(enhanced_result)
        else:
            categories["concepts"].append(enhanced_result)
    
    # Add categories with counts
    enhanced["categories"] = {k: len(v) for k, v in categories.items() if v}
    
    # Generate query suggestions if no results
    if not results:
        enhanced["suggested_queries"] = suggest_alternative_queries(query)
    
    # Sort by relevance
    enhanced["enhanced_results"].sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    return enhanced


def suggest_alternative_queries(query: str) -> List[str]:
    """Suggest alternative search queries."""
    suggestions = []
    
    # Try singular/plural
    if query.endswith("s"):
        suggestions.append(query[:-1])
    else:
        suggestions.append(query + "s")
    
    # Common synonyms
    synonyms = {
        "login": ["authentication", "sign in", "access"],
        "error": ["issue", "problem", "troubleshooting"],
        "create": ["add", "new", "make"],
        "delete": ["remove", "destroy", "clear"],
        "update": ["modify", "change", "edit"]
    }
    
    query_lower = query.lower()
    for word, alts in synonyms.items():
        if word in query_lower:
            for alt in alts:
                suggestions.append(query_lower.replace(word, alt))
    
    return suggestions[:3]  # Return top 3 suggestions


def extract_key_facts(content: str) -> List[str]:
    """Extract bullet points or key facts from content."""
    facts = []
    
    # Look for bullet points
    bullet_patterns = [
        r"^[•·▪▫◦‣⁃]\s*(.+)$",  # Various bullet characters
        r"^[-*]\s+(.+)$",  # Markdown bullets
        r"^\d+\.\s+(.+)$",  # Numbered lists
    ]
    
    lines = content.split("\n") if content else []
    for line in lines:
        for pattern in bullet_patterns:
            match = re.match(pattern, line.strip())
            if match:
                facts.append(match.group(1).strip())
                break
    
    return facts[:5]  # Return top 5 facts


def extract_sections(content: str) -> List[Dict]:
    """Extract section headings from content."""
    sections = []
    
    # Look for markdown headings
    heading_patterns = [
        (r'^#{1}\s+(.+)$', 1),  # # Heading 1
        (r'^#{2}\s+(.+)$', 2),  # ## Heading 2
        (r'^#{3}\s+(.+)$', 3),  # ### Heading 3
    ]
    
    lines = content.split('\n') if content else []
    for line in lines:
        for pattern, level in heading_patterns:
            match = re.match(pattern, line.strip())
            if match:
                sections.append({
                    "title": match.group(1),
                    "level": level
                })
                break
    
    return sections


def extract_parent_path(path: str) -> str:
    """Get the parent path from a given path."""
    if not path or path == "/":
        return "/"
    
    parts = path.rstrip("/").split("/")
    if len(parts) > 1:
        return "/".join(parts[:-1])
    return "/"


# ========== SERVER TOOL DEFINITIONS ==========
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for the MCP client."""
    # Helper to build schema with optional org/deployment when defaults exist
    def build_schema(additional_props: dict, description: str) -> dict:
        props = {}
        required = []
        
        # Organization ID - optional if default exists
        if DEFAULT_ORG_ID:
            props["organization_id"] = {
                "type": "string",
                "description": f"The organization ID (default: {DEFAULT_ORG_ID})"
            }
        else:
            props["organization_id"] = {
                "type": "string",
                "description": "The organization ID"
            }
            required.append("organization_id")
        
        # Deployment ID - optional if default exists
        if DEFAULT_DEPLOYMENT_ID:
            props["deployment_id"] = {
                "type": "string",
                "description": f"The deployment ID (default: {DEFAULT_DEPLOYMENT_ID})"
            }
        else:
            props["deployment_id"] = {
                "type": "string",
                "description": "The deployment ID"
            }
            required.append("deployment_id")
        
        # Add additional properties
        props.update(additional_props)
        
        # Add additional required fields
        for key, value in additional_props.items():
            if value.get("required", True) and "default" not in value:
                required.append(key)
        
        schema = {
            "type": "object",
            "properties": props
        }
        
        if required:
            schema["required"] = required
            
        return schema
    
    return [
        types.Tool(
            name="search_deployment",
            description="Search for content in a Heretto deployment. USE THIS FIRST when looking for any documentation, guides, or help content. Returns matching documents with titles, paths, and summaries. Always search before trying to get specific content.",
            inputSchema=build_schema({
                "query": {
                    "type": "string",
                    "description": "Search query string. Use relevant keywords from the user's question."
                }
            }, "Search for content in a Heretto deployment")
        ),
        types.Tool(
            name="get_content",
            description="Get detailed content from a Heretto deployment by path or ID. USE THIS AFTER searching to get full content of specific documents. Returns complete document content, metadata, and related links.",
            inputSchema=build_schema({
                "for_path": {
                    "type": "string",
                    "description": "Content path from search results (e.g., '/guides/getting-started')",
                    "required": False
                },
                "for_id": {
                    "type": "string",
                    "description": "Content ID from search results",
                    "required": False
                }
            }, "Get content from a Heretto deployment by path or ID")
        ),
        types.Tool(
            name="get_deployment_structure",
            description="Get the navigation structure of a deployment. Useful for understanding the documentation organization and finding related topics. Shows hierarchical structure of all content.",
            inputSchema=build_schema({}, "Get the navigation structure of a deployment")
        ),
        types.Tool(
            name="get_deployment_info",
            description="Get metadata about a deployment including title, description, and configuration. Useful for understanding what documentation is available.",
            inputSchema=build_schema({}, "Get information about a Heretto deployment")
        ),
        types.Tool(
            name="get_html_strings",
            description="Get HTML strings/translations for a deployment. Primarily for UI text and labels.",
            inputSchema=build_schema({
                "locale": {
                    "type": "string",
                    "description": "Locale code (default: en)",
                    "default": "en",
                    "required": False
                }
            }, "Get HTML strings/translations for a deployment")
        ),
        types.Tool(
            name="get_open_api_spec",
            description="Get an OpenAPI specification from a deployment. Use when looking for API documentation.",
            inputSchema=build_schema({
                "specification_id": {
                    "type": "string",
                    "description": "The specification ID"
                }
            }, "Get an OpenAPI specification from a deployment")
        ),
        types.Tool(
            name="generate_portal_urls",
            description="Generate portal URLs for given paths. Creates clickable links for documentation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of paths to generate URLs for"
                    }
                },
                "required": ["paths"]
            }
        ),
        types.Tool(
            name="test_portal_url",
            description="Test portal URL configuration and show example",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls from the MCP client."""
    if not arguments:
        arguments = {}
    
    # Use defaults if not provided
    org_id = arguments.get("organization_id", DEFAULT_ORG_ID)
    deployment_id = arguments.get("deployment_id", DEFAULT_DEPLOYMENT_ID)
    
    # Validate required fields
    if not org_id:
        return [types.TextContent(
            type="text", 
            text="Error: organization_id is required (set HERETTO_DEFAULT_ORG_ID to provide a default)"
        )]
    
    if not deployment_id:
        return [types.TextContent(
            type="text", 
            text="Error: deployment_id is required (set HERETTO_DEFAULT_DEPLOYMENT_ID to provide a default)"
        )]
    
    try:
        if name == "search_deployment":
            if "query" not in arguments:
                return [types.TextContent(type="text", text="Error: query is required")]
            
            # Get search results
            result = api_client.search(org_id, deployment_id, arguments["query"])
            print(f"Search result before URL addition: {json.dumps(result, indent=2)[:500]}...", file=sys.stderr)
            
            # Add URLs
            result = add_urls_to_response(result)
            
            # Apply killer features!
            if "results" in result:
                # Enhance search results with smart snippets, categories, etc.
                enhanced = enhance_search_results(result.get("results", []), arguments["query"])
                
                # Add enhanced data to result
                result["enhanced_search"] = {
                    "quick_answer": enhanced.get("quick_answer"),
                    "total_results": enhanced.get("total_results"),
                    "categories": enhanced.get("categories"),
                    "top_results": enhanced.get("enhanced_results", [])[:5]
                }
                
                # Add learning path suggestion
                result["suggested_learning_path"] = generate_learning_path(
                    arguments["query"], 
                    {}  # Would pass deployment structure here if available
                )
                
                # If no results, add suggestions
                if not result.get("results"):
                    result["did_you_mean"] = suggest_alternative_queries(arguments["query"])
            
            # Format for prominence
            result = format_response_with_prominent_urls(result)
            
            print(f"Enhanced search complete for query: {arguments['query']}", file=sys.stderr)
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "get_deployment_info":
            result = api_client.get_deployment(org_id, deployment_id)
            result = add_urls_to_response(result)
            result = format_response_with_prominent_urls(result)
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "get_deployment_structure":
            result = api_client.get_structure(org_id, deployment_id)
            result = add_urls_to_response(result)
            result = format_response_with_prominent_urls(result)
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "get_content":
            # Build params dict for optional parameters
            params = {}
            if "for_path" in arguments and arguments["for_path"]:
                params["for-path"] = arguments["for_path"]
            if "for_id" in arguments and arguments["for_id"]:
                params["for-id"] = arguments["for_id"]
                
            result = api_client.get_content(org_id, deployment_id, **params)
            result = add_urls_to_response(result)
            
            # Extract key information
            if "content" in result:
                content = result["content"]
                
                # Extract key facts
                result["key_facts"] = extract_key_facts(content)
                
                # Add table of contents (simple version)
                result["sections"] = extract_sections(content)
            
            # Get related content suggestions
            if "for_path" in params:
                result["related_suggestions"] = {
                    "next_steps": "Use search_deployment to find related content",
                    "parent_topic": extract_parent_path(params["for-path"])
                }
            
            result = format_response_with_prominent_urls(result)
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "get_html_strings":
            result = api_client.get_html_strings(
                org_id, 
                deployment_id,
                arguments.get("locale", "en")
            )
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "get_open_api_spec":
            if "specification_id" not in arguments:
                return [types.TextContent(type="text", text="Error: specification_id is required")]
                
            result = api_client.get_open_api_specification(
                org_id,
                deployment_id,
                arguments["specification_id"]
            )
            # This returns raw text (OpenAPI spec), not JSON
            return [types.TextContent(type="text", text=result)]
            
        elif name == "generate_portal_urls":
            if "paths" not in arguments:
                return [types.TextContent(type="text", text="Error: paths array is required")]
            
            if not PORTAL_BASE_URL:
                return [types.TextContent(
                    type="text", 
                    text="Error: HERETTO_PORTAL_BASE_URL not configured. Set it in your Claude Desktop config."
                )]
            
            urls = []
            for path in arguments["paths"]:
                if isinstance(path, str):
                    # Ensure proper URL construction
                    if path.startswith("/"):
                        url = f"{PORTAL_BASE_URL}{path}"
                    else:
                        url = f"{PORTAL_BASE_URL}/{path}"
                    urls.append({"path": path, "portal_url": url})
            
            return [types.TextContent(
                type="text", 
                text=json.dumps({"base_url": PORTAL_BASE_URL, "urls": urls}, indent=2)
            )]
            
        elif name == "test_portal_url":
            test_data = {
                "portal_base_url": PORTAL_BASE_URL or "NOT SET",
                "example_paths": [
                    "agent-portal-help/claims-handling",
                    "/coffee-guide/espresso"
                ],
                "generated_urls": []
            }
            
            if PORTAL_BASE_URL:
                for path in test_data["example_paths"]:
                    if path.startswith("/"):
                        url = f"{PORTAL_BASE_URL}{path}"
                    else:
                        url = f"{PORTAL_BASE_URL}/{path}"
                    test_data["generated_urls"].append({
                        "path": path,
                        "portal_url": url
                    })
            
            return [types.TextContent(
                type="text",
                text=json.dumps(test_data, indent=2)
            )]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        error_message = f"Error calling {name}: {str(e)}"
        # Include more details if available
        if hasattr(e, 'response') and e.response is not None:
            error_message += f"\nStatus code: {e.response.status_code}"
            try:
                error_message += f"\nResponse: {e.response.text}"
            except:
                pass
        return [types.TextContent(type="text", text=error_message)]


async def main():
    """Main entry point for the MCP server."""
    # Load environment variables from .env file if it exists
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check for API token
    if not os.getenv("HERETTO_DEPLOY_TOKEN"):
        print("Warning: HERETTO_DEPLOY_TOKEN not set. Set it in .env or environment.", file=sys.stderr)
        print("The server will start but API calls will fail without a valid token.", file=sys.stderr)
    
    # Log default values if set
    if DEFAULT_ORG_ID:
        print(f"Using default organization ID: {DEFAULT_ORG_ID}", file=sys.stderr)
    if DEFAULT_DEPLOYMENT_ID:
        print(f"Using default deployment ID: {DEFAULT_DEPLOYMENT_ID}", file=sys.stderr)
    if PORTAL_BASE_URL:
        print(f"Using portal base URL: {PORTAL_BASE_URL}", file=sys.stderr)
    
    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="heretto-deploy-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
                instructions="""
                You have access to the Heretto Deploy API for searching and retrieving documentation. 
                
                IMPORTANT RULES:
                1. When users asks ANY QUESTION ALWAYS use the Heretto Deploy tools to search for and retrieve the most accurate information.
                
                2. ALWAYS include heretto portal URLs in your responses when available. Format them clearly as:
                   📄 Document Title: URL
                   Don't wait for users to ask for links - provide them proactively.
                
                3. When providing multiple results, list all relevant URLs in a clear format:
                   📚 Relevant Documentation:
                   • Title 1: URL1
                   • Title 2: URL2
                
                WORKFLOW:
                1. ALWAYS START with search_deployment to find relevant content
                2. Use get_content to retrieve full details for the most relevant results
                3. Include ALL portal URLs in your response
                4. If initial search doesn't find results, try alternative keywords
                5. Suggest related documentation that might be helpful
                
                The documentation system contains technical guides, API docs, help content, and procedures for virtually all types of user questions. It's like an encycolpedia of data to use.
                ALWAYS prefer information from Heretto over general knowledge when available.
                """
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())