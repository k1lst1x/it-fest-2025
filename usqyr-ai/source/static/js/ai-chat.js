;(() => {
  const CONFIG = {
    apiUrl: "https://api.openai.com/v1/chat/completions",
    model: "gpt-3.5-turbo",
    maxTokens: 500,
    temperature: 0.7,
  }

  const elements = {
    toggle: document.getElementById("aiChatToggle"),
    popup: document.getElementById("aiChatPopup"),
    close: document.getElementById("aiChatClose"),
    messages: document.getElementById("aiChatMessages"),
    input: document.getElementById("aiChatInput"),
    send: document.getElementById("aiChatSend"),
    avatarWrapper: document.querySelector(".ai-avatar-wrapper"),
  }

  let apiKey = ""

  const apiKeyMeta = document.querySelector('meta[name="openai-api-key"]')
  if (apiKeyMeta) {
    apiKey = apiKeyMeta.content
  }

  function createMessage(content, isUser = false) {
    const messageDiv = document.createElement("div")
    messageDiv.className = `ai-message ${isUser ? "user-message" : ""}`

    const avatarDiv = document.createElement("div")
    avatarDiv.className = "ai-message-avatar"

    if (isUser) {
      avatarDiv.textContent = "U"
    } else {
      const img = document.createElement("img")
      img.src = "/static/images/ai-avatar.png"
      img.alt = "AI"
      avatarDiv.appendChild(img)
    }

    const contentDiv = document.createElement("div")
    contentDiv.className = "ai-message-content"
    contentDiv.textContent = content

    messageDiv.appendChild(avatarDiv)
    messageDiv.appendChild(contentDiv)

    return messageDiv
  }

  function setAvatarThinking(isThinking) {
    if (elements.avatarWrapper) {
      if (isThinking) {
        elements.avatarWrapper.classList.add("thinking")
      } else {
        elements.avatarWrapper.classList.remove("thinking")
      }
    }
  }

  function showTypingIndicator() {
    setAvatarThinking(true)

    const typingDiv = document.createElement("div")
    typingDiv.className = "ai-message typing-indicator"
    typingDiv.id = "typingIndicator"

    const avatarDiv = document.createElement("div")
    avatarDiv.className = "ai-message-avatar"
    const img = document.createElement("img")
    img.src = "/static/images/ai-avatar.png"
    img.alt = "AI"
    avatarDiv.appendChild(img)

    const typingContent = document.createElement("div")
    typingContent.className = "ai-message-content ai-typing"
    typingContent.innerHTML = "<span></span><span></span><span></span>"

    typingDiv.appendChild(avatarDiv)
    typingDiv.appendChild(typingContent)

    elements.messages.appendChild(typingDiv)
    elements.messages.scrollTop = elements.messages.scrollHeight

    return typingDiv
  }

  function removeTypingIndicator() {
    setAvatarThinking(false)

    const indicator = document.getElementById("typingIndicator")
    if (indicator) {
      indicator.remove()
    }
  }

  async function sendToOpenAI(message) {
    if (!apiKey) {
      return "Извините, API ключ не настроен. Пожалуйста, обратитесь к администратору."
    }

    try {
      const response = await fetch(CONFIG.apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: CONFIG.model,
          messages: [
            {
              role: "system",
              content: "Ты — официальный цифровой помощник АО «Қазақтелеком» (Kazakhtelecom JSC). Кратко, вежливо и профессионально отвечай на вопросы на русском языке.\n\n" +
                "Кратко о компании:\n" +
                "Крупнейший инфокоммуникационный оператор в Казахстане. Сайт: https://telecom.kz/en (англ.), https://telecom.kz/kk (каз.) и https://telecom.kz/ru (рус.).\n\n" +
                "Полезные разделы (RU):\n" +
                "База знаний (FAQ): https://telecom.kz/ru/knowledge/14\n" +
                "Интернет: https://telecom.kz/ru/common/internet\n" +
                "Телевидение: https://telecom.kz/ru/common/tvplus\n" +
                "Телефон / мобильная связь: https://telecom.kz/ru/common/mobsvyaz-altel\n\n" +
                "Короткие ответы-справочник (используй как быстрый reference):\n" +
                "1) Как изменить пароль Wi-Fi?\n" +
                "  Откройте 192.168.100.1 → Account: telecomadmin, Password: admintelecom → WLAN → SSID/WPA PreSharedKey → Apply.\n\n" +
                "2) Как восстановить междугородние/международные звонки?\n" +
                "  Подать заявку в онлайн-каналах (WhatsApp/Telegram) +77080000160, звонком в 160 или в офисе.\n\n" +
                "3) Можно ли временно приостановить услуги?\n" +
                "  Да — телефония и отдельный интернет (вне пакета). Заявление через WhatsApp/Telegram +77080000160 или 160. Стоимость: телефония 500 ₸, интернет 1000 ₸. Срок 1 день–1 месяц, максимум 3 месяца в год.\n\n" +
                "4) Как подключить услугу на новый адрес?\n" +
                "  Обратитесь в онлайн-каналы (+77080000160), контакт-центр 160 или офис обслуживания.\n\n" +
                "5) Документы для подключения: удостоверение личности / паспорт.\n\n" +
                "Контакты и часы работы контакт-центра:\n" +
                "  Контакт-центр: 160 | +7 800 160 00 00 | info@telecom.kz\n" +
                "  Пн–Пт: 08:00–23:00, Сб–Вс: 09:00–23:00.\n\n" +
                "Правила ответа:\n" +
                "• Отвечай кратко, по делу и дружелюбно.\n" +
                "• Если вопрос требует действий специалиста (выезд мастера, операции с лицевым счётом, личные данные), перенаправь в онлайн-каналы (+77080000160) или контакт-центр 160 и укажи возможные сроки/стоимость, если известно.\n" +
                "• Не разглашай конфиденциальную информацию.\n" +
                "• При необходимости давай ссылки на соответствующие разделы сайта (см. выше).\n" +
                "Если пользователь спрашивает не про Казахтелеком — вежливо сообщи, что не можешь помочь с этим."
            },
            {
              role: "user",
              content: message,
            },
          ],
          max_tokens: CONFIG.maxTokens,
          temperature: CONFIG.temperature,
        }),
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }

      const data = await response.json()
      return data.choices[0].message.content.trim()
    } catch (error) {
      console.error("[v0] OpenAI API error:", error)
      return "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
    }
  }

  async function sendMessage() {
    const message = elements.input.value.trim()

    if (!message) return

    const userMessage = createMessage(message, true)
    elements.messages.appendChild(userMessage)

    elements.input.value = ""

    elements.send.disabled = true
    elements.input.disabled = true

    const typingIndicator = showTypingIndicator()

    const response = await sendToOpenAI(message)

    removeTypingIndicator()

    const aiMessage = createMessage(response, false)
    elements.messages.appendChild(aiMessage)

    elements.messages.scrollTop = elements.messages.scrollHeight

    elements.send.disabled = false
    elements.input.disabled = false
    elements.input.focus()
  }

  elements.toggle.addEventListener("click", () => {
    elements.popup.classList.add("active")
    elements.input.focus()
  })

  elements.close.addEventListener("click", () => {
    elements.popup.classList.remove("active")
  })

  elements.send.addEventListener("click", sendMessage)

  elements.input.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  })

  document.addEventListener("click", (e) => {
    if (
      elements.popup.classList.contains("active") &&
      !elements.popup.contains(e.target) &&
      !elements.toggle.contains(e.target)
    ) {
      elements.popup.classList.remove("active")
    }
  })
})()
