# Phase 7 Manual Test Checklist

Test scenarios that validate the user experience flow.

## Flow 1: First-time user

- [v] Open the app, sees welcome screen with examples
- [v] System status shows correct chunk count and model
- [v] Sidebar shows 0 questions and 0 tokens
- [v] Click an example query
- [v] Spinner appears during processing
- [v] Answer appears with proper formatting
- [v] Sources can be expanded
- [v] Sidebar updates with question count and tokens

## Flow 2: Conversation continuation

- [v] After first question, type a follow-up question
- [v] Both questions appear in chat history
- [v] Sidebar accumulates totals correctly
- [v] Source colors match similarity (🟢 high, 🟡 medium, 🔴 low)
- [v] Source text is visible when expanded

## Flow 3: Empty state and reset

- [v] Click "Nova conversa"
- [v] History clears, examples reappear
- [v] Sidebar resets to 0
- [v] Can start fresh conversation

## Flow 4: Out-of-scope queries

- [v] Ask about something not in podcast (e.g., crypto)
- [v] System responds gracefully ("Não encontrei...")
- [v] No hallucinations
- [v] Sources still show what was searched

## Flow 5: Cross-episode queries

- [v] Ask broad question (e.g., "Sobre o que falaram em episódios de tecnologia?")
- [v] Answer cites multiple episodes
- [v] Citations link to different episodes correctly

## Performance benchmarks

- [v] Initial load: < 30s (first time)
- [v] Query response: < 15s
- [v] Subsequent queries: < 5s (after model warm)
- [v] No memory leak after 10+ queries