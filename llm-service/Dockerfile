FROM ollama/ollama:latest

ENV OLLAMA_HOST=0.0.0.0:8080
ENV OLLAMA_MODELS=/root/.ollama/models
ENV OLLAMA_KEEP_ALIVE=-1
ENV OLLAMA_NUM_PARALLEL=2

RUN set -e; \
    ollama serve & \
    SERVER_PID=$!; \
    for i in $(seq 1 30); do \
      if ollama list >/dev/null 2>&1; then break; fi; \
      sleep 1; \
    done; \
    ollama pull SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0; \
    ollama list; \
    kill $SERVER_PID || true

EXPOSE 8080
ENTRYPOINT ["/bin/ollama"]
CMD ["serve"]
