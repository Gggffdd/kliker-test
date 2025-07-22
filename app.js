// Конфигурация слота
const symbols = ['🍒', '🍋', '🍇', '🍉', '🔔', '💎', '7️⃣', '🐶'];
const reelCount = 5;
const rowsVisible = 3;
const symbolHeight = 100; // px

// Состояние игры
let balance = 1000;
let currentBet = 100;
let isSpinning = false;

// DOM элементы
const reels = [];
const balanceEl = document.getElementById('balance');
const betEl = document.getElementById('bet');
const spinBtn = document.getElementById('spin-btn');
const betUpBtn = document.getElementById('bet-up');
const betDownBtn = document.getElementById('bet-down');
const winMessageEl = document.getElementById('win-message');

// Инициализация барабанов
for (let i = 1; i <= reelCount; i++) {
    const reel = document.getElementById(`reel${i}`);
    reels.push(reel);
    
    // Создаем символы для барабана
    for (let j = 0; j < 20; j++) {
        const symbolIndex = Math.floor(Math.random() * symbols.length);
        createSymbol(reel, symbols[symbolIndex], j);
    }
}

// Функции
function createSymbol(reel, symbol, position) {
    const symbolEl = document.createElement('div');
    symbolEl.className = 'symbol';
    symbolEl.textContent = symbol;
    symbolEl.style.top = `${position * symbolHeight}px`;
    reel.appendChild(symbolEl);
    return symbolEl;
}

function spin() {
    if (isSpinning || balance < currentBet) return;
    
    balance -= currentBet;
    updateBalance();
    isSpinning = true;
    spinBtn.disabled = true;
    winMessageEl.style.opacity = '0';
    
    // Сбрасываем победные стили
    document.querySelectorAll('.symbol').forEach(s => {
        s.classList.remove('winning-symbol');
    });
    
    // Запускаем вращение каждого барабана
    const spins = [];
    for (let i = 0; i < reelCount; i++) {
        spins.push(spinReel(reels[i], i));
    }
    
    // Обрабатываем результаты
    Promise.all(spins).then(results => {
        calculateWin(results);
        isSpinning = false;
        spinBtn.disabled = false;
    });
}

function spinReel(reel, index) {
    return new Promise(resolve => {
        const symbols = reel.querySelectorAll('.symbol');
        const duration = 2000 + index * 500; // Разное время для эффекта каскада
        
        // Генерируем конечную позицию
        const targetPosition = Math.floor(Math.random() * symbols.length);
        
        // Анимация
        let startTime = null;
        
        function animate(time) {
            if (!startTime) startTime = time;
            const elapsed = time - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeProgress = 1 - Math.pow(1 - progress, 3); // easing
            
            // Прокрутка
            symbols.forEach(symbol => {
                const pos = parseFloat(symbol.style.top || 0);
                const newPos = (pos - easeProgress * 1000) % (symbols.length * symbolHeight);
                symbol.style.top = `${newPos}px`;
            });
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                // Фиксация результата
                const resultSymbols = [];
                for (let i = 0; i < rowsVisible; i++) {
                    const position = (targetPosition + i) % symbols.length;
                    resultSymbols.push(symbols[position].textContent);
                }
                resolve(resultSymbols);
            }
        }
        
        requestAnimationFrame(animate);
    });
}

function calculateWin(results) {
    // Транспонируем матрицу результатов (строки -> линии выплат)
    const lines = [];
    for (let i = 0; i < rowsVisible; i++) {
        lines.push(results.map(reel => reel[i]));
    }
    
    // Проверка выигрышных линий
    let totalWin = 0;
    
    lines.forEach((line, lineIndex) => {
        let symbol = line[0];
        let count = 1;
        
        for (let i = 1; i < line.length; i++) {
            if (line[i] === symbol) {
                count++;
            } else {
                break;
            }
        }
        
        // Выплаты (чем больше одинаковых символов - тем больше выплата)
        if (count >= 3) {
            const winMultiplier = getWinMultiplier(symbol, count);
            const winAmount = currentBet * winMultiplier;
            totalWin += winAmount;
            
            // Подсветка выигрышных символов
            for (let i = 0; i < count; i++) {
                const reel = reels[i];
                const symbols = reel.querySelectorAll('.symbol');
                const winSymbol = symbols[(symbols.length - lineIndex - 1) % symbols.length];
                winSymbol.classList.add('winning-symbol');
            }
        }
    });
    
    // Обновляем баланс и показываем сообщение
    if (totalWin > 0) {
        balance += totalWin;
        updateBalance();
        showWinMessage(totalWin);
    }
}

function getWinMultiplier(symbol, count) {
    const symbolValues = {
        '💎': [0, 0, 5, 20, 100],
        '7️⃣': [0, 0, 4, 15, 75],
        '🔔': [0, 0, 3, 10, 50],
        '🐶': [0, 0, 3, 10, 50],
        '🍉': [0, 0, 2, 7, 25],
        '🍇': [0, 0, 2, 5, 20],
        '🍋': [0, 0, 1, 3, 15],
        '🍒': [0, 0, 1, 2, 10]
    };
    
    return symbolValues[symbol][count - 1] || 0;
}

function showWinMessage(amount) {
    winMessageEl.textContent = `ВЫИГРЫШ: ${amount}💰`;
    winMessageEl.style.opacity = '1';
    
    // Автоскрытие сообщения
    setTimeout(() => {
        winMessageEl.style.opacity = '0';
    }, 3000);
}

function updateBalance() {
    balanceEl.textContent = balance;
    betEl.textContent = currentBet;
    
    // Автокорректировка ставки если баланс меньше
    if (currentBet > balance) {
        currentBet = Math.max(10, Math.floor(balance / 10) * 10);
    }
}

function changeBet(amount) {
    const newBet = currentBet + amount;
    if (newBet >= 10 && newBet <= balance) {
        currentBet = newBet;
        updateBalance();
    }
}

// Обработчики событий
spinBtn.addEventListener('click', spin);
betUpBtn.addEventListener('click', () => changeBet(10));
betDownBtn.addEventListener('click', () => changeBet(-10));

// Инициализация
updateBalance();
