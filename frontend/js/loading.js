// ===== PUZZLE LOADING ANIMATION MANAGER =====

class PuzzleLoadingManager {
    constructor() {
        this.loadingScreen = document.getElementById('loadingScreen');
        this.loadingText = document.getElementById('loadingText');
        this.totalDuration = 3000; // tempo mínimo de exibição do loading
        this.puzzleGrid = null;
        this.puzzlePieces = [];
        this.shuffleInterval = null;
        this.shuffleTimeout = null;
        this.isAssembling = false;
    }

    /**
     * Cria o HTML do puzzle
     */
    createPuzzleHTML() {
        const html = `
            <div class="puzzle-container">
                <div class="puzzle-grid" id="puzzleGrid">
                    <!-- Peças serão adicionadas aqui -->
                </div>
            </div>
        `;
        
        this.loadingScreen.innerHTML = html + `<p class="loading-text" id="loadingText">Montando seu acesso...</p>`;
        this.puzzleGrid = document.getElementById('puzzleGrid');
        this.loadingText = document.getElementById('loadingText');
    }

    /**
     * Cria as 16 peças do puzzle embaralhadas
     */
    createPuzzlePieces() {
        const pieces = [];
        const slots = [];
        
        // Criar as 16 peças (4x4)
        for (let i = 0; i < 16; i++) {
            const row = Math.floor(i / 4);
            const col = i % 4;
            slots.push({ row, col });
            
            pieces.push({
                id: i,
                correctPosition: i,
                row: row,
                col: col,
                x: col * 75, // 300px / 4 = 75px
                y: row * 75
            });
        }

        // Embaralhar as peças
        this.puzzlePieces = pieces.sort(() => Math.random() - 0.5);
        const shuffledSlots = slots.sort(() => Math.random() - 0.5);

        // Renderizar no HTML
        this.puzzlePieces.forEach((piece, index) => {
            const pieceElement = document.createElement('div');
            pieceElement.className = 'puzzle-piece';
            pieceElement.id = `piece-${piece.id}`;
            pieceElement.style.setProperty('--x', `-${piece.x}px`);
            pieceElement.style.setProperty('--y', `-${piece.y}px`);
            pieceElement.style.setProperty('--delay', `${index * 0.08}s`);
            pieceElement.style.setProperty('--rotation', `${Math.random() * 10 - 5}deg`);
            pieceElement.style.setProperty('--slot-x', `${shuffledSlots[index].col * 25}%`);
            pieceElement.style.setProperty('--slot-y', `${shuffledSlots[index].row * 25}%`);
            pieceElement.dataset.correctPosition = piece.correctPosition;
            pieceElement.dataset.currentPosition = index;
            pieceElement.dataset.originX = piece.x;
            pieceElement.dataset.originY = piece.y;
            pieceElement.dataset.currentSlotX = shuffledSlots[index].col;
            pieceElement.dataset.currentSlotY = shuffledSlots[index].row;
            
            this.puzzleGrid.appendChild(pieceElement);
        });
    }

    shufflePieces() {
        if (this.isAssembling) {
            return;
        }

        const pieceElements = Array.from(document.querySelectorAll('.puzzle-piece'));
        if (pieceElements.length === 0) {
            return;
        }

        const slots = [];
        for (let row = 0; row < 4; row++) {
            for (let col = 0; col < 4; col++) {
                slots.push({ row, col });
            }
        }

        const shuffledSlots = slots.sort(() => Math.random() - 0.5);

        pieceElements.forEach((piece, index) => {
            const target = shuffledSlots[index];
            piece.style.setProperty('--slot-x', `${target.col * 25}%`);
            piece.style.setProperty('--slot-y', `${target.row * 25}%`);
            piece.style.setProperty('--rotation', `${Math.random() * 14 - 7}deg`);
            piece.dataset.currentSlotX = target.col;
            piece.dataset.currentSlotY = target.row;
        });
    }

    startShuffling() {
        this.stopShuffling();
        this.shufflePieces();
        this.shuffleInterval = setInterval(() => {
            this.shufflePieces();
        }, 260);
    }

    stopShuffling() {
        if (this.shuffleInterval) {
            clearInterval(this.shuffleInterval);
            this.shuffleInterval = null;
        }

        if (this.shuffleTimeout) {
            clearTimeout(this.shuffleTimeout);
            this.shuffleTimeout = null;
        }
    }

    /**
     * Inicia a animação de loading
     * @param {string} message - Mensagem de carregamento
     * @returns {Promise} Promise que resolve quando animação termina
     */
    show(message = null) {
        // Criar estrutura do puzzle
        this.isAssembling = false;
        this.createPuzzleHTML();
        this.createPuzzlePieces();

        // Mostrar a tela de loading
        this.loadingScreen.classList.add('active');

        // Atualizar mensagem se fornecida
        if (message) {
            this.loadingText.textContent = message;
        }

        this.startShuffling();

        // Retornar uma Promise que resolve quando a animação de embaralhamento termina
        return new Promise((resolve) => {
            this.shuffleTimeout = setTimeout(() => {
                resolve();
            }, this.totalDuration);
        });
    }

    /**
     * Monta o puzzle (sucesso)
     */
    async assemblePuzzle() {
        this.isAssembling = true;
        this.stopShuffling();

        const pieces = document.querySelectorAll('.puzzle-piece');
        
        // Animar cada peça se encaixando no lugar correto
        for (let i = 0; i < pieces.length; i++) {
            const piece = pieces[i];
            const correctPos = parseInt(piece.dataset.correctPosition);
            
            // Calcular a posição correta
            const row = Math.floor(correctPos / 4);
            const col = correctPos % 4;
            
            // Animar para a posição correta
            setTimeout(() => {
                piece.classList.add('correct');
                piece.style.transition = 'all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)';
                piece.style.setProperty('--slot-x', `${col * 25}%`);
                piece.style.setProperty('--slot-y', `${row * 25}%`);
                piece.style.setProperty('--x', `-${col * 75}px`);
                piece.style.setProperty('--y', `-${row * 75}px`);
            }, i * 50);
        }

        // Aguardar a última peça se encaixar
        await new Promise(resolve => setTimeout(resolve, pieces.length * 50 + 800));

        // Efeito de brilho final
        this.puzzleGrid.classList.add('completed');
        this.loadingText.classList.add('success');
        this.loadingText.textContent = 'Acesso desbloqueado!';
    }

    /**
     * Falha - puzzle não se monta
     */
    async failPuzzle() {
        this.isAssembling = false;
        this.stopShuffling();

        const pieces = document.querySelectorAll('.puzzle-piece');
        
        // Fazer todas as peças sacodirem
        pieces.forEach(piece => {
            piece.classList.add('wrong');
        });

        this.puzzleGrid.classList.remove('completed');
        this.puzzleGrid.classList.add('denied');
        this.loadingText.classList.remove('success');
        this.loadingText.classList.add('error');
        this.loadingText.textContent = 'Acesso negado!';

        // Aguardar a animação de erro
        await new Promise(resolve => setTimeout(resolve, 850));

        // Voltar ao estado anterior
        pieces.forEach(piece => {
            piece.classList.remove('wrong');
        });

        this.puzzleGrid.classList.remove('denied');
        this.loadingText.classList.remove('error');
    }

    /**
     * Esconde a tela de loading
     */
    hide() {
        this.stopShuffling();
        this.loadingScreen.classList.remove('active');
    }
}

// Inicializar globalmente
const loadingManager = new PuzzleLoadingManager();


