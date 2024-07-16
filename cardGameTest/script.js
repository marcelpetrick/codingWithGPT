document.addEventListener('DOMContentLoaded', () => {
    const deckElement = document.getElementById('deck');
    const handElement = document.getElementById('hand');

    const suits = ['hearts', 'diamonds', 'clubs', 'spades'];
    const values = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];

    let deck = [];
    let flippedCards = [];

    // Create deck
    suits.forEach(suit => {
        values.forEach(value => {
            const card = {
                suit,
                value,
                element: createCardElement(value, suit)
            };
            deck.push(card);
            deckElement.appendChild(card.element);
        });
    });

    // Shuffle deck
    function shuffle(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
    }

    shuffle(deck);

    // Draw card on click
    deckElement.addEventListener('click', () => {
        if (deck.length > 0) {
            const card = deck.pop();
            handElement.appendChild(card.element);
            animateCard(card.element);
            card.element.addEventListener('click', () => {
                flipCard(card);
            });
        }
    });

    // Create card element
    function createCardElement(value, suit) {
        const card = document.createElement('div');
        card.classList.add('card', 'card-back');
        card.dataset.value = value;
        card.dataset.suit = suit;

        const front = document.createElement('div');
        front.classList.add('card-front');
        front.innerText = `${value} ${suit}`;

        const back = document.createElement('div');
        back.classList.add('card-back');

        card.appendChild(front);
        card.appendChild(back);

        return card;
    }

    // Animate card drawing
    function animateCard(card) {
        gsap.fromTo(card, { y: -50, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5 });
    }

    // Flip card
    function flipCard(card) {
        card.element.classList.toggle('flipped');
        flippedCards.push(card);
        if (flippedCards.length === 2) {
            checkMatch();
        }
    }

    // Check for match
    function checkMatch() {
        const [card1, card2] = flippedCards;
        if (card1.value === card2.value && card1.suit === card2.suit) {
            alert('Match found!');
            flippedCards = [];
        } else {
            setTimeout(() => {
                card1.element.classList.remove('flipped');
                card2.element.classList.remove('flipped');
                flippedCards = [];
            }, 1000);
        }
    }
});
