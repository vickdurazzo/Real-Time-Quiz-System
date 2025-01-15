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
quiz_project/
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
│   │   └── api_collection/ # Arquivos estáticos para a API
│   │       
│   └── templates/          # Templates HTML
├── DB/                     # Info dos bancos de dados do Projeto
│   └── models/
│       ├── PostgreSQL model Sistema Gameficado de Quiz_.hck.json
│       └── tables_scripts.sql
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

1. **Clonar o Repositório:**
   ```bash
   git clone https://github.com/seu_usuario/real-time-quiz-game.git
   cd real-time-quiz-game
   ```

2. **Configuração do Ambiente com Docker:**
   Certifique-se de ter o **Docker** e o **Docker Compose** instalados em sua máquina.

   1. Construa e inicie os containers:
      ```bash
      docker-compose up --build
      ```

   2. Acesse o aplicativo em: [http://localhost:5000](http://localhost:5000).

   3. Para parar os containers, use:
      ```bash
      docker-compose down
      ```

3. **(Opcional) Executar Localmente sem Docker:**
   Caso prefira não usar Docker, siga as etapas abaixo:

   1. **Criar e Ativar o Ambiente Virtual:**
      ```bash
      python3 -m venv venv
      source venv/bin/activate  # No Windows: venv\Scripts\activate
      ```

   2. **Instalar Dependências:**
      ```bash
      pip install -r requirements.txt
      ```

   3. **Configurar o Redis e PostgreSQL:**
      - Certifique-se de que o Redis e PostgreSQL estão instalados e em execução na sua máquina.
      - Atualize as configurações de conexão no projeto, se necessário.

   4. **Executar o Projeto:**
      ```bash
      flask run
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
