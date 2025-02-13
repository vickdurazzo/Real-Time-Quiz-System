# Real-Time Quiz Game

## Sobre o Projeto

O **Real-Time Quiz Game** é uma aplicação que permite a criação e gestão de quizzes em tempo real. Professores podem criar quizzes interativos, enquanto alunos participam, respondem perguntas. A aplicação também apresenta rankings detalhados ao final de cada jogo.

## Funcionalidades Principais

- **Criação de Quizzes:** Professores podem criar quizzes personalizados com perguntas de múltipla escolha.
- **Participação dos Jogadores:** Jogadores podem ingressar nos quizzes e enviar suas respostas em tempo real.
- **Envio de Perguntas em Tempo Real:** As perguntas são transmitidas dinamicamente para os jogadores.
- **Ranking:** Ao final do quiz, é exibido um ranking com a pontuação dos jogadores.

## Tecnologias Utilizadas

### Backend
- **Flask:** Framework web em Python utilizado para criar as rotas e a lógica do servidor.
- **Redis:** Banco de dados em memória usado para gerenciar estados em tempo real e desempenho de alto nível.
- **Postgresql**  Banco de dados relacional para armazenar dados persistentes.

### Frontend
- **HTML e Jinja2:** Para templates dinâmicos e renderização de páginas.

### Outras Dependências
- **Python:** Linguagem principal do projeto.
- **Bibliotecas:**
  - Flask-Bootstrap (para estilização básica)
  - Outros serviços integrados via Redis
  
## Estrutura do Projeto

```plaintext
REAL-TIME-QUIZ-SYSTEM/
├── app/
│   ├── __init__.py         # Inicializa a aplicação Flask e as extensões
│   ├── models.py           # Definição de modelos de dados
│   ├── config.py           # Configurações da aplicação
│   ├── routes/             # Módulos com as rotas do projeto
│   │   ├── auth.py         # Autenticação e controle de acesso
│   │   ├── game.py         # Lógica do jogo
│   │   ├── home.py         # Página inicial
│   │   └── quiz.py         # Gerenciamento de quizzes
│   ├── services/           # Módulos de serviços
│   │   ├── __init__.py     # Inicializa os serviços
│   │   ├── redis_service.py # Serviço de Redis do Projeto
│   │   └── websocket.py    # Serviço de WebSockets
│   ├── static/             # Arquivos estáticos (CSS, JS, Imagens)
│   │   ├── style.css       # Estilo CSS básico
│   │   └── api_collection/ # Arquivo da Api
│   │   └── imgs/           # Arquivo de imagens projeto
│   │       
│   └── templates/          # Templates HTML
├── DB/                     # Info dos bancos de dados do Projeto
│   └── init_ddl/
│       └── init.sql        # Script inicializador banco de dados         
│   └── modelo/
│       ├── PostgreSQL model Sistema Gameficado de Quiz_.hck.json # Modelo do banco de dados Relacional
│       └── mapeamento_chaves_redis.yaml                          # Documentação das chaves do processo
│
├── requirements.txt        # Dependências do projeto
├── run.py                  # Arquivo principal para executar a aplicação
└── LICENSE.md              # Licença do projeto
└── README.md               # Documentação do projeto
└── tests/
    ├── __init__.py
    └── test_game.py       # Arquivo para teste da logica do jogo
```

## Configuração do Ambiente

## Pré-requisitos

Antes de começar, certifique-se de ter as seguintes ferramentas instaladas no seu computador:

- [Docker](https://www.docker.com/products/docker-desktop) (inclui o Docker Compose)
- [Docker Compose](https://docs.docker.com/compose/)

## Instruções de execução no modo de desenvolvimento

Siga os passos abaixo para rodar a aplicação localmente em modo de desenvolvimento:

### 1. Clonar o repositório

Clone o repositório da aplicação para o seu computador:

```bash
git clone https://github.com/seu-usuario/Real-Time-Quiz-System.git
cd Real-Time-Quiz-System
```
### 2. Criar as imagens Docker

Construir as imagens necessárias usando o Docker Compose:

```
docker-compose build
```
### 3. Subir os containers

Subir os containers com o Docker Compose:
```
docker-compose up -d
```
### 4. Acessar o container da aplicação

Para acessar o container da aplicação e interagir com ele, use o comando docker exec:
```
docker exec -it quiz_app /bin/bash
```

### 5. Rodar a aplicação Flask

Dentro do container, execute o comando abaixo para iniciar a aplicação Flask:
```
python run.py
```

### 6. Acessar a aplicação no navegador

Agora que a aplicação está rodando, você pode acessá-la através do seu navegador:

- URL: http://localhost:5000

## Observações

- A aplicação estará rodando no modo de desenvolvimento, então qualquer alteração nos arquivos do código fonte será automaticamente refletida na aplicação.
- O Flask servirá a aplicação na URL [http://localhost:5000](http://localhost:5000).
- Para parar a aplicação, use o comando:

```bash
docker-compose down
```

## Uso

### Iniciar um Quiz
1. Acesse a rota `/start_quiz/<quiz_id>` para iniciar um quiz.
2. Envie perguntas dinamicamente usando a funcionalidade de broadcast.

### Participar de um Quiz
- Use a rota `/quiz/<quiz_id>/join` para ingressar no quiz como jogador.
- Responda às perguntas enviadas em tempo real.

### Visualizar Ranking
- Ao término do quiz, acesse a rota `/quiz/<quiz_id>/results` para visualizar o ranking final.

## Contribuição

Sinta-se à vontade para contribuir com melhorias para o projeto:

1. Faça um fork do repositório.
2. Crie uma branch para sua feature:
   ```bash
   git checkout -b feature/nova-feature
   ```
3. Envie suas mudanças:
   ```bash
   git push origin feature/nova-feature
   ```
4. Abra um pull request.

## Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo `LICENSE` para mais informações.

---

Desenvolvido com ❤️ por Vick.
