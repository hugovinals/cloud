import datetime
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    now = datetime.datetime.utcnow().isoformat()
    return func.HttpResponse(f"OK - Server time: {now}", status_code=200)
