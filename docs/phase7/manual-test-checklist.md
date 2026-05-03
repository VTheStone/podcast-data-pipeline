# Phase 7 Manual Test Checklist

Test scenarios that validate the user experience flow. All scenarios
were validated successfully during MVP delivery.

## Flow 1: First-time user

- [x] Open the app, sees welcome screen with examples
- [x] System status shows correct chunk count and model
- [x] Sidebar shows 0 questions and 0 tokens
- [x] Click an example query
- [x] Spinner appears during processing
- [x] Answer appears with proper formatting
- [x] Sources can be expanded
- [x] Sidebar updates with question count and tokens

## Flow 2: Conversation continuation

- [x] After first question, type a follow-up question
- [x] Both questions appear in chat history
- [x] Sidebar accumulates totals correctly
- [x] Source colors match similarity (🟢 high, 🟡 medium, 🔴 low)
- [x] Source text is visible when expanded

## Flow 3: Empty state and reset

- [x] Click "New conversation"
- [x] History clears, examples reappear
- [x] Sidebar resets to 0
- [x] Can start fresh conversation

## Flow 4: Out-of-scope queries

- [x] Ask about something not in podcast (e.g., crypto)
- [x] System responds gracefully
- [x] No hallucinations
- [x] Sources still show what was searched

## Flow 5: Cross-episode queries

- [x] Ask broad question (e.g., topics across episodes)
- [x] Answer cites multiple episodes
- [x] Citations link to different episodes correctly

## Performance benchmarks

- [x] Initial load: < 30s (first time)
- [x] Query response: < 15s
- [x] Subsequent queries: < 5s (after model warm)
- [x] No memory leak after 10+ queries

## Replicating these tests for a different podcast

When adapting to a different podcast, customize the queries in each flow
to match the new content domain. The flows themselves remain valid
regardless of the podcast.