# Base image com Python
FROM python:3.9-slim

# Diretório de trabalho dentro do container
WORKDIR /REAL-TIME-QUIZ-SYSTEM

# Copiar os arquivos do projeto para o container
COPY . .

# Instalar o módulo venv e criar o ambiente virtual
RUN python -m venv /opt/venv

# Ativar o ambiente virtual e instalar dependências
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Configuração da variável de ambiente para usar o Python do ambiente virtual
ENV PATH="/opt/venv/bin:$PATH"

# Definição do comando padrão como bash, permitindo que o usuário interaja com o container
CMD ["/bin/bash"]