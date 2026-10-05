import os, requests
def show(name, r):
    print(name, r.status_code, r.text[:300].replace(os.environ.get("GEMINI_API_KEY","~~"),"***"))
k=os.environ.get("GEMINI_API_KEY","")
print("gemini key len", len(k), "prefix", k[:4])
for m in ("gemini-2.5-flash-lite","gemini-2.5-flash","gemini-3.5-flash-lite"):
    for mime in (True, False):
        gc={"temperature":0.5,"maxOutputTokens":2000}
        if mime: gc["responseMimeType"]="application/json"
        r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",headers={"x-goog-api-key":k},json={"contents":[{"parts":[{"text":"Reply with JSON {\"ok\":1}"}]}],"generationConfig":gc},timeout=60)
        show(f"{m} json={mime}", r)
g=os.environ.get("GROQ_API_KEY","")
if g:
    r=requests.post("https://api.groq.com/openai/v1/chat/completions",headers={"Authorization":"Bearer "+g},json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":"say ok"}],"max_tokens":10},timeout=60); show("groq",r)
o=os.environ.get("OPENROUTER_API_KEY","")
if o:
    r=requests.post("https://openrouter.ai/api/v1/chat/completions",headers={"Authorization":"Bearer "+o},json={"model":"meta-llama/llama-3.3-70b-instruct:free","messages":[{"role":"user","content":"say ok"}],"max_tokens":10},timeout=60); show("openrouter",r)
