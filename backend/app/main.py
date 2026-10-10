from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from .config import settings
from .routes import router
from .retention import cleanup_expired


@asynccontextmanager
async def lifespan(app):
    # Startup cleanup is additional to the dedicated supervised worker.
    cleanup_expired()
    yield


app = FastAPI(title='Document Q&A', version='1.0.0', lifespan=lifespan,
              docs_url='/api/docs' if settings.environment != 'production' else None,
              redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
    allow_credentials=True, allow_methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE'],
    allow_headers=['Content-Type', 'X-CSRF-Token'])


class BodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        limit = 101 * 1024 * 1024  # Hard cap, includes multipart envelope.
        headers = dict(scope.get('headers', []))
        try:
            declared = int(headers.get(b'content-length', b'0'))
        except ValueError:
            declared = limit + 1
        if declared > limit:
            return await JSONResponse({'detail': 'Request body too large'}, status_code=413)(scope, receive, send)
        consumed = 0
        async def limited_receive():
            nonlocal consumed
            message = await receive()
            consumed += len(message.get('body', b''))
            if consumed > limit:
                raise HTTPException(413, 'Request body too large')
            return message
        await self.app(scope, limited_receive, send)


app.add_middleware(BodyLimitMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Default validation errors can echo passwords, questions, and PDF input.
    return JSONResponse({'detail': [{'loc': e['loc'], 'msg': e['msg'], 'type': e['type']}
        for e in exc.errors()]}, status_code=422)


@app.middleware('http')
async def security_headers(request: Request, call_next):
    # Block cross-origin unsafe calls, including unauthenticated login/registration.
    origin = request.headers.get('origin')
    if request.method not in {'GET', 'HEAD', 'OPTIONS'} and origin and origin not in settings.cors_origins:
        return JSONResponse({'detail': 'Origin forbidden'}, status_code=403)
    try:
        response = await call_next(request)
    except Exception:
        # Catch before ServerErrorMiddleware/Uvicorn can log SQL parameters or provider bodies.
        response = JSONResponse({'detail': 'Service unavailable. Please try again later.'}, status_code=503)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    if settings.cookie_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


@app.exception_handler(Exception)
async def safe_error(request, exc):
    # Never print exceptions containing private document/provider content.
    return JSONResponse({'detail': 'Service unavailable. Please try again later.'}, status_code=503)


@app.get('/api/health')
def health():
    return {'status': 'ok'}


app.include_router(router)
