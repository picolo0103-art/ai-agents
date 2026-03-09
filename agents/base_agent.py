"""Base agent — Groq with llama-3.3-70b-specdec (speculative decoding ≈ 3× faster). Sync + async streaming."""
import json
import re
from typing import Any, Dict, List

from groq import AsyncGroq, Groq
from config.settings import settings


class BaseAgent:
    # llama-3.3-70b-specdec uses speculative decoding:
    #   - same quality as llama-3.3-70b-versatile
    #   - ~3× lower time-to-first-token (typically < 0.5s)
    MODEL = "llama-3.3-70b-specdec"
    MAX_TOKENS = 2048          # 2 k is plenty; was 4 k but added ~1 s latency
    MAX_TOOL_ITERATIONS = 6    # prevent infinite tool-call loops

    def __init__(self, name: str, system_prompt: str, tools: List[Dict], client_context: str = ""):
        self.name = name
        self._base_system_prompt = system_prompt
        self.client_context = client_context
        self.tools = tools
        self.client = Groq(api_key=settings.groq_api_key)
        self.async_client = AsyncGroq(api_key=settings.groq_api_key)
        self.conversation: List[Dict] = []

    @property
    def system_prompt(self) -> str:
        if self.client_context:
            return f"{self._base_system_prompt}\n\n{self.client_context}"
        return self._base_system_prompt

    # ── Public API ──────────────────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        """Blocking chat — used by REST endpoint."""
        self.conversation.append({"role": "user", "content": user_message})
        text = self._run_loop()
        self.conversation.append({"role": "assistant", "content": text})
        return text

    async def chat_stream(self, user_message: str):
        """
        Async generator — yields events for the WebSocket.
        Event types:
          {"type": "tool_call",   "name": "tool_name"}
          {"type": "tool_result", "name": "tool_name"}
          {"type": "token",       "text": "..."}
          {"type": "end"}
        """
        self.conversation.append({"role": "user", "content": user_message})
        messages: List[Dict] = [
            {"role": "system", "content": self.system_prompt}
        ] + list(self.conversation)

        response_text = ""
        iterations = 0

        while iterations < self.MAX_TOOL_ITERATIONS:
            iterations += 1
            kwargs: Dict = {}
            if self.tools:
                kwargs["tools"] = self.tools
                kwargs["tool_choice"] = "auto"

            stream = await self.async_client.chat.completions.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                messages=messages,
                stream=True,
                **kwargs,
            )

            # Accumulate tool calls and text for this iteration
            tool_calls_accum: Dict[int, Dict] = {}
            iteration_text = ""

            async for chunk in stream:
                choice = chunk.choices[0]
                delta = choice.delta

                # ── Text token ──────────────────────────────────────────
                if delta.content:
                    iteration_text += delta.content
                    response_text += delta.content
                    yield {"type": "token", "text": delta.content}

                # ── Tool call chunks ────────────────────────────────────
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_accum:
                            name = self._sanitize_tool_name(
                                (tc.function.name or "") if tc.function else ""
                            )
                            tool_calls_accum[idx] = {"id": tc.id or "", "name": name, "arguments": ""}
                            if name:
                                yield {"type": "tool_call", "name": name}
                        else:
                            if tc.id:
                                tool_calls_accum[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.arguments:
                                    tool_calls_accum[idx]["arguments"] += tc.function.arguments

            if tool_calls_accum:
                # Build the assistant tool-call message
                tool_calls_list = [
                    {
                        "id": tool_calls_accum[idx]["id"],
                        "type": "function",
                        "function": {
                            "name": tool_calls_accum[idx]["name"],
                            "arguments": tool_calls_accum[idx]["arguments"],
                        },
                    }
                    for idx in sorted(tool_calls_accum.keys())
                ]
                messages.append({
                    "role": "assistant",
                    "content": iteration_text or None,
                    "tool_calls": tool_calls_list,
                })

                # Execute tools and collect results
                for tc in tool_calls_list:
                    tool_name = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except Exception:
                        args = {}
                    result = self._execute_tool(tool_name, args)
                    yield {"type": "tool_result", "name": tool_name}
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(result, ensure_ascii=False),
                    })

                response_text = ""  # reset for next iteration

            else:
                # Final text response — save to history
                self.conversation.append({"role": "assistant", "content": response_text})
                yield {"type": "end"}
                return

        # Safety: max iterations reached
        self.conversation.append({"role": "assistant", "content": response_text})
        yield {"type": "end"}

    def reset(self):
        self.conversation = []

    # ── Sync loop (REST) ────────────────────────────────────────────────

    def _run_loop(self) -> str:
        messages: List[Dict] = [
            {"role": "system", "content": self.system_prompt}
        ] + list(self.conversation)

        for _ in range(self.MAX_TOOL_ITERATIONS):
            kwargs: Dict = {}
            if self.tools:
                kwargs["tools"] = self.tools
                kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                messages=messages,
                **kwargs,
            )
            message = response.choices[0].message

            if not message.tool_calls:
                return message.content or ""

            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {
                         "name": self._sanitize_tool_name(tc.function.name),
                         "arguments": tc.function.arguments,
                     }}
                    for tc in message.tool_calls
                ],
            })
            for tc in message.tool_calls:
                tool_name = self._sanitize_tool_name(tc.function.name)
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                result = self._execute_tool(tool_name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        return message.content or ""

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _sanitize_tool_name(name: str) -> str:
        """Strip junk the model sometimes appends to tool names (e.g. 'tool={...}')."""
        # Keep only leading word characters (letters, digits, underscore)
        match = re.match(r'^[\w]+', name)
        return match.group(0) if match else name

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        handler = self._tool_handlers().get(tool_name)
        if handler is None:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return handler(**tool_input)
        except Exception as exc:
            return {"error": str(exc)}

    def _tool_handlers(self) -> Dict:
        return {}
