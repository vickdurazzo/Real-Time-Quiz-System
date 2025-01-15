# Dockerfile

# Base image com Python
FROM python:3.9-slim

# Diretório de trabalho dentro do container
WORKDIR /app

# Copiar os arquivos do projeto para o container
COPY . .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Configuração da variável de ambiente para o Flask
ENV FLASK_APP=run.py
ENV FLASK_ENV=development

# Porta que a aplicação usará
EXPOSE 5000

# Comando para rodar a aplicação
CMD ["flask", "run", "--host=0.0.0.0"]
