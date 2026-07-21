from fastapi import FastAPI

app = FastAPI(title = "Jobpilot API")

@app.get("/")
def root():
    return{
        "message":"Jobpilot API is running"
    }
