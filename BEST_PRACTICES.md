### Good Practice
```
User: "How do I submit a claim?"
Claude: 
1. search_deployment("claim submission")
2. Found "Claims Submission Process" at /agent-portal/claims/submission
3. get_content(for_path="/agent-portal/claims/submission")
4. Provides step-by-step instructions with portal URL
```

### Better Practice
```
User: "I'm getting an error when submitting claims"
Claude:
1. search_deployment("claim submission error")
2. search_deployment("claim troubleshooting")
3. get_content for most relevant troubleshooting guide
4. Provides specific solution based on documentation
```

## Integration Tips

### 1. Set Default Values
Configure defaults in Claude Desktop config:
```json
{
  "env": {
    "HERETTO_DEFAULT_ORG_ID": "your-org",
    "HERETTO_DEFAULT_DEPLOYMENT_ID": "your-deployment",
    "HERETTO_PORTAL_BASE_URL": "https://your-docs.com"
  }
}
```

### 2. Portal URLs
With HERETTO_PORTAL_BASE_URL configured:
- All paths automatically get portal_url added
- Claude can provide clickable links
- Users can navigate directly to source documentation

### 3. Fallback Strategies
If search returns no results:
1. Try broader terms
2. Check deployment structure for navigation
3. Use get_deployment_info to understand available content
4. Try partial words or word stems

## Common Patterns by Industry

### Software Documentation
- Search for: "API", "SDK", "integration", "configuration"
- Look in: `/api/`, `/developers/`, `/reference/`

### Product Documentation  
- Search for: "manual", "guide", "specifications", "features"
- Look in: `/products/`, `/guides/`, `/tutorials/`

### Internal Knowledge Base
- Search for: "policy", "procedure", "process", "FAQ"
- Look in: `/policies/`, `/procedures/`, `/help/`

## Debugging Tips

### When Search Returns Nothing
1. Check spelling
2. Try single words instead of phrases
3. Use test_portal_url to verify configuration
4. Try get_deployment_structure to browse manually

### When Content is Missing
1. Verify the path is correct
2. Try using content ID instead of path
3. Check if content requires special permissions

### Performance Tips
1. Cache frequently accessed content mentally
2. Use specific searches to reduce result sets
3. Get structure once, then navigate by memory

## Advanced Techniques

### Cross-Reference Multiple Sources
```
1. Search for main topic
2. Note related topics in results
3. get_content for 2-3 most relevant documents
4. Synthesize comprehensive answer
```

### Build Mental Map
```
1. get_deployment_structure early in conversation
2. Understand content organization
3. Use structure knowledge to find related content
```

### Anticipate Follow-ups
When answering, also search for:
- Related troubleshooting guides
- Next steps in process
- Common questions about the topic

## Summary

The key to effective Heretto Deploy API usage is:
1. **Always search first** - Don't assume, verify with current docs
2. **Be thorough** - Multiple searches often yield better results  
3. **Follow the path** - Use document paths to find related content
4. **Provide links** - Always include portal URLs for users
5. **Learn the structure** - Understanding organization helps future searches

Remember: The documentation in Heretto is the authoritative source. Always prefer it over general knowledge when available.# Heretto Deploy API Best Practices

## Overview

This guide provides strategies for effectively using the Heretto Deploy API through the MCP server to retrieve documentation and help content.

## Effective Search Strategies

### 1. Start with Search
Always begin with `search_deployment` before trying to get specific content:
- Cast a wide net first with general terms
- If no results, try variations or synonyms
- Use terms from the user's domain/industry

### 2. Search Query Tips
- **Product names**: "La Pavoni", "Thunderbird", "Agent Portal"
- **Task-based**: "how to", "configure", "install", "troubleshoot"
- **Feature-based**: "claims", "authentication", "API", "integration"
- **Problem-based**: "error", "issue", "cannot", "failed"

### 3. Progressive Refinement
```
First search: "claims"
If too many results: "claims submission"
If too few results: "claim" (singular) or "insurance claim"
```

## Workflow Patterns

### Pattern 1: Answer a How-To Question
```
1. search_deployment with task keywords ("how to submit claim")
2. Review results, identify most relevant path
3. get_content with the specific path
4. Extract step-by-step instructions
5. generate_portal_urls for direct links
```

### Pattern 2: Troubleshooting
```
1. search_deployment with error/symptom keywords
2. Look for troubleshooting guides or FAQs
3. get_content for detailed solutions
4. Check related documents for context
```

### Pattern 3: Feature Documentation
```
1. get_deployment_structure to understand organization
2. search_deployment for feature name
3. get_content for overview and details
4. Look for related API docs if applicable
```

### Pattern 4: Comprehensive Research
```
1. get_deployment_info for system overview
2. search_deployment with broad terms
3. get_deployment_structure to find related topics
4. get_content for multiple relevant documents
5. Synthesize information across sources
```

## Content Types in Heretto

### Concept Topics
- Overview and explanation of features
- Background information
- Best practices

### Task Topics
- Step-by-step procedures
- How-to guides
- Tutorials

### Reference Topics
- API documentation
- Configuration parameters
- Technical specifications

### Troubleshooting Topics
- Common issues and solutions
- Error messages
- FAQs

## Search Optimization

### Use Multiple Searches
Don't stop at one search. Try:
- Different word forms (singular/plural)
- Synonyms (delete/remove, create/add)
- Related concepts (authentication → login, security)

### Leverage Metadata
Search results include:
- **title**: Document title
- **path**: Location in hierarchy (useful for finding related content)
- **description**: Summary of content
- **portal_url**: Direct link to documentation

### Understanding Paths
Paths reveal document organization:
- `/guides/` - How-to guides
- `/api/` - API documentation  
- `/troubleshooting/` - Problem solving
- `/concepts/` - Explanations
- `/reference/` - Technical details

## Example Interactions

### Good Practice
```
User: "How do I submit a claim?"