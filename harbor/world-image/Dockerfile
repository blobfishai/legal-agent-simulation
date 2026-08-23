# Shared world image for every legal-agent-simulation Harbor task.
# Built ONCE by harbor/generate.py (--build-image); per-task compose files
# reference it by tag and select the task with the TASK_ID env var.
FROM python:3.12-slim
WORKDIR /world
# The multi-GB evidence layer changes least often. Keep it ahead of runtime
# code so a verifier/runtime edit does not rebuild and re-export the corpus.
COPY corpus /world/corpus
COPY contracts /world/contracts
COPY server.py oracle.py v2runtime.py v3dialects.py evidence.py paging.py wire_errors.py product_workflows.py query_dsl.py v21_verifier_runtime.py shim.py start.sh world.json /world/
ARG ORACLE_PROOF_SHA256=""
ENV ORACLE_PROOF_SHA256=${ORACLE_PROOF_SHA256} PYTHONUNBUFFERED=1
EXPOSE 8972
CMD ["bash", "/world/start.sh"]
