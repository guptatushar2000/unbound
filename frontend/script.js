// frontend/script.js
document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chat-container');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const userSelect = document.getElementById('user-select');
    
    let conversationId = null;
    
    function addMessage(content, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user' : 'bot');
        
        // Process content for code blocks
        if (!isUser && content.includes('```')) {
            const parts = content.split('```');
            let formattedContent = '';
            
            for (let i = 0; i < parts.length; i++) {
                if (i % 2 === 0) {
                    // Regular text
                    formattedContent += parts[i];
                } else {
                    // Code block
                    formattedContent += `<pre><code>${parts[i]}</code></pre>`;
                }
            }
            
            messageDiv.innerHTML = formattedContent;
        } else {
            // Process for links (simple version - for production, use a safer approach)
            if (!isUser && content.includes('http')) {
                const linkRegex = /(https?:\/\/[^\s]+)/g;
                content = content.replace(linkRegex, '<a href="$1" target="_blank">$1</a>');
                messageDiv.innerHTML = content;
            } else {
                messageDiv.textContent = content;
            }
        }
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;
        
        const userId = userSelect.value;
        
        addMessage(message, true);
        messageInput.value = '';
        messageInput.focus();
        
        try {
            const response = await fetch('/api/chat/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: userId,
                    message: message,
                    conversation_id: conversationId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            const data = await response.json();
            conversationId = data.conversation_id;
            
            addMessage(data.response, false);
        } catch (error) {
            console.error('Error:', error);
            addMessage('Sorry, I encountered an error while processing your request. Please try again.', false);
        }
    }
    
    // Function to use suggestion
    window.useSuggestion = function(text) {
        messageInput.value = text;
        sendMessage();
    };
    
    // Send on button click
    sendButton.addEventListener('click', sendMessage);
    
    // Send on Enter key
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // Reset conversation when user changes
    userSelect.addEventListener('change', function() {
        conversationId = null;
        chatContainer.innerHTML = '';
        addMessage(`Hi, I'm your Financial Batch & Results Assistant. How can I help you today?`, false);
    });
    
    // Initialize with welcome message
    addMessage("Welcome to the Financial Batch & Results Chatbot! You can:\n\n1. Start batch runs (CCAR, RiskApetite, Stress)\n2. Check run status\n3. View run logs\n4. Get stress test results\n5. Get allowance results\n\nHow can I help you today?", false);
});