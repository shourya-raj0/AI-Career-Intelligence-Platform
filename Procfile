# Fallback for PaaS builds that use Nixpacks instead of the Dockerfile
# (e.g. Heroku-style Procfiles). The Dockerfile is the primary path.
web: streamlit run frontend/app.py --server.port ${PORT:-8501} --server.address 0.0.0.0
