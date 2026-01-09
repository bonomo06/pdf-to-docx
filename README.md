# PDF to DOCX Converter API

API REST em Python para conversão de documentos PDF para DOCX, com autenticação Bearer Token e medidas de segurança.

## 🚀 Funcionalidades

- ✅ Conversão de PDF para DOCX via upload de arquivo
- ✅ Conversão de PDF para DOCX via URL
- ✅ Autenticação via Bearer Token
- ✅ Rate Limiting por IP
- ✅ Validação de tipo e tamanho de arquivo
- ✅ Proteção contra timing attacks
- ✅ Logging estruturado
- ✅ Documentação automática (Swagger/OpenAPI)

## 📋 Pré-requisitos

- Python 3.10+
- pip

## 🔧 Instalação

1. Clone o repositório ou navegue até a pasta do projeto:

```bash
cd pdf-to-docx
```

2. Crie um ambiente virtual:

```bash
python -m venv venv
```

3. Ative o ambiente virtual:

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

4. Instale as dependências:

```bash
pip install -r requirements.txt
```

## ⚙️ Configuração

O arquivo `.env` já vem com um token gerado automaticamente. Para produção, gere um novo token:

```bash
python -c "import secrets; print(f'API_BEARER_TOKEN={secrets.token_urlsafe(48)}')"
```

### Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `API_BEARER_TOKEN` | Token de autenticação da API | Auto-gerado |
| `MAX_FILE_SIZE_MB` | Tamanho máximo do arquivo em MB | 50 |
| `ALLOWED_HOSTS` | Hosts permitidos (separados por vírgula) | * |
| `RATE_LIMIT_REQUESTS` | Máximo de requisições por janela | 100 |
| `RATE_LIMIT_WINDOW_SECONDS` | Janela de tempo do rate limit em segundos | 3600 |

## 🏃 Executando

### Desenvolvimento

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Ou diretamente:

```bash
python -m app.main
```

### Produção

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📖 Documentação da API

Após iniciar o servidor, acesse:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔌 Endpoints

### Health Check

```
GET /health
```

Verifica se a API está funcionando. Não requer autenticação.

### Converter PDF (Upload)

```
POST /convert/file
Authorization: Bearer <seu_token>
Content-Type: multipart/form-data

file: <arquivo.pdf>
```

### Converter PDF (URL)

```
POST /convert/url
Authorization: Bearer <seu_token>
Content-Type: application/json

{
    "url": "https://exemplo.com/documento.pdf"
}
```

## 📝 Exemplos de Uso

### cURL - Upload de Arquivo

```bash
curl -X POST "http://localhost:8000/convert/file" \
  -H "Authorization: Bearer sk_pdf2docx_a7f3b9c1d4e6f8g2h5i7j0k3l6m9n1o4p7q0r3s6t9u2v5w8x1y4z7" \
  -F "file=@documento.pdf" \
  -o documento.docx
```

### cURL - Via URL

```bash
curl -X POST "http://localhost:8000/convert/url" \
  -H "Authorization: Bearer sk_pdf2docx_a7f3b9c1d4e6f8g2h5i7j0k3l6m9n1o4p7q0r3s6t9u2v5w8x1y4z7" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://exemplo.com/documento.pdf"}' \
  -o documento.docx
```

### Python - Requests

```python
import requests

# Upload de arquivo
with open("documento.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/convert/file",
        headers={"Authorization": "Bearer sk_pdf2docx_a7f3b9c1d4e6f8g2h5i7j0k3l6m9n1o4p7q0r3s6t9u2v5w8x1y4z7"},
        files={"file": f}
    )

with open("documento.docx", "wb") as f:
    f.write(response.content)
```

```python
import requests

# Via URL
response = requests.post(
    "http://localhost:8000/convert/url",
    headers={
        "Authorization": "Bearer sk_pdf2docx_a7f3b9c1d4e6f8g2h5i7j0k3l6m9n1o4p7q0r3s6t9u2v5w8x1y4z7",
        "Content-Type": "application/json"
    },
    json={"url": "https://exemplo.com/documento.pdf"}
)

with open("documento.docx", "wb") as f:
    f.write(response.content)
```

## 🔒 Segurança

Esta API implementa as seguintes medidas de segurança:

1. **Autenticação Bearer Token**: Todas as rotas de conversão requerem token válido
2. **Comparação de Tempo Constante**: Previne timing attacks na validação do token
3. **Rate Limiting**: Limita requisições por IP para prevenir abuso
4. **Validação de Arquivos**: Verifica magic bytes do PDF antes da conversão
5. **Limite de Tamanho**: Restringe tamanho máximo de arquivos
6. **Limpeza de Arquivos Temporários**: Remove arquivos temporários após conversão
7. **Nomes de Arquivo Seguros**: Usa UUIDs para arquivos temporários
8. **Timeout em Downloads**: Limita tempo de download de URLs externas

## 🐳 Docker (Opcional)

Crie um arquivo `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build e execução:

```bash
docker build -t pdf-to-docx-api .
docker run -p 8000:8000 --env-file .env pdf-to-docx-api
```

## 📄 Licença

MIT License
