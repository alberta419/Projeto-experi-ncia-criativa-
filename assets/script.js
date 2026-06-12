console.log('[assets/script.js] loaded');

document.addEventListener('DOMContentLoaded', () => {
  console.log('[assets/script.js] DOMContentLoaded');
  // --- ELEMENTOS GLOBAIS E POPUPS ---
  const popupLogin = document.getElementById('popupLogin');
  const popupCadastro = document.getElementById('popupCadastro');
  const fecharPopupLogin = document.getElementById('fecharPopupLogin');
  const fecharPopupCadastro = document.getElementById('fecharPopupCadastro');
  const botaoAreaCliente = document.getElementById('botaoAreaCliente');
  const abrirCadastroDoLogin = document.getElementById('abrirCadastroDoLogin');
  const abrirLoginDoCadastro = document.getElementById('abrirLoginDoCadastro');
  const loginSubmitBtn = document.getElementById('loginSubmitBtn');
  const popupNovoPet = document.getElementById('popupNovoPet');
  const btnAbrirPopupPet = document.getElementById('btnAbrirPopupPet');
  const fecharPopupPet = document.getElementById('fecharPopupPet');
  const hamburgerBtn = document.querySelector('.hamburger-btn');
  const navLinks = document.querySelector('.nav-links');


  function abrirPopup(popupElement) {
    if (popupElement) popupElement.classList.add('active');
  }

  function fecharPopup(popupElement) {
    if (popupElement) {
      popupElement.classList.remove('active');
      
      // Limpa os campos de senha sempre que o popup for fechado
      popupElement.querySelectorAll('.password-container input').forEach(input => {
        input.value = '';
        input.type = 'password'; // Garante que volte a esconder as letras
      });
      popupElement.querySelectorAll('.toggle-password').forEach(icon => icon.textContent = '👁️');
    }
  }

  if (botaoAreaCliente) {
    botaoAreaCliente.addEventListener('click', (e) => {
      e.preventDefault();
      abrirPopup(popupLogin);
    });
  }
  else {
    // Fallback: listener delegado caso o elemento seja adicionado dinamicamente
    document.addEventListener('click', (e) => {
      const target = e.target;
      if (!target) return;
      if (target.id === 'botaoAreaCliente' || target.closest && target.closest('#botaoAreaCliente')) {
        e.preventDefault();
        console.log('[assets/script.js] delegated click detected for #botaoAreaCliente');
        abrirPopup(popupLogin);
      }
    });
  }

  if (fecharPopupLogin) fecharPopupLogin.addEventListener('click', () => fecharPopup(popupLogin));
  if (fecharPopupCadastro) fecharPopupCadastro.addEventListener('click', () => fecharPopup(popupCadastro));

  if (abrirLoginDoCadastro) {
    abrirLoginDoCadastro.addEventListener('click', (e) => {
      e.preventDefault();
      fecharPopup(popupCadastro);
      abrirPopup(popupLogin);
    });
  }

  if (abrirCadastroDoLogin) {
    abrirCadastroDoLogin.addEventListener('click', (e) => {
      e.preventDefault();
      fecharPopup(popupLogin);
      abrirPopup(popupCadastro);
    });
  }

  // Permite fechar os popups clicando no fundo (no próprio elemento .popup-wrapper)
  if (popupLogin) {
    popupLogin.addEventListener('click', (e) => { if (e.target === popupLogin) fecharPopup(popupLogin); });
  }
  if (popupCadastro) {
    popupCadastro.addEventListener('click', (e) => { if (e.target === popupCadastro) fecharPopup(popupCadastro); });
  }

  if (btnAbrirPopupPet) {
    btnAbrirPopupPet.addEventListener('click', () => abrirPopup(popupNovoPet));
  }
  if (fecharPopupPet) {
    fecharPopupPet.addEventListener('click', () => fecharPopup(popupNovoPet));
  }
  if (popupNovoPet) {
    popupNovoPet.addEventListener('click', (e) => { if (e.target === popupNovoPet) fecharPopup(popupNovoPet); });
  }

  if (loginSubmitBtn) {
    // Removido o eventListener que impedia o envio. 
    // Agora o botão do form fará o POST natural pro FastAPI (ação="/login").
  }

  if (window.location.hash === '#login' && popupLogin) {
    abrirPopup(popupLogin);
  }

  // --- LÓGICA DE VALIDAÇÃO DO FORMULÁRIO DE CADASTRO ---
  const form = document.getElementById('registerForm');
  if (form) {
    const name = document.getElementById('fullName');
    const phone = document.getElementById('phone');
    const password = document.getElementById('password');
    const confirmPassword = document.getElementById('confirmPassword');
    const emailEl = document.getElementById('email');
    const cpfEl = document.getElementById('cpf');
    const birthEl = document.getElementById('birth');

    const nameError = document.getElementById('nameError');
    const emailError = document.getElementById('emailError');
    const cpfError = document.getElementById('cpfError');
    const birthError = document.getElementById('birthError');
    const phoneError = document.getElementById('phoneError');
    const passwordError = document.getElementById('passwordError');
    const confirmPasswordError = document.getElementById('confirmPasswordError');

    // --- Funções de Máscara ---
    const applyMask = (el, mask) => el.addEventListener('input', () => el.value = mask(el.value));
    const phoneMask = v => v.replace(/\D/g, '').replace(/^(\d{2})(\d)/g, '($1)$2').replace(/(\d{4,5})(\d{4})$/, '$1-$2');
    const cpfMask = v => v.replace(/\D/g, '').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
    const birthMask = v => v.replace(/\D/g, '').replace(/(\d{2})(\d)/, '$1/$2').replace(/(\d{2})(\d)/, '$1/$2');

    applyMask(phone, phoneMask);
    applyMask(cpfEl, cpfMask);
    applyMask(birthEl, birthMask);

    // --- Funções de Validação ---
    const setValidationStatus = (el, errorEl, message) => {
      errorEl.textContent = message || '';
      el.classList.toggle('invalid', !!message);
      el.classList.toggle('valid', !message);
      return !message;
    };

    const validate = (el, errorEl, condition, message) => {
      if (el.value.trim().length === 0) {
        errorEl.textContent = '';
        el.classList.remove('invalid', 'valid');
        return false;
      }
      return setValidationStatus(el, errorEl, condition ? '' : message);
    }

    const validateName = () => validate(name, nameError, /^[a-zA-Z\s]{8,50}$/.test(name.value), 'Nome precisa ter entre 8 e 50 letras.');
    const validateEmail = () => validate(emailEl, emailError, emailEl.checkValidity(), 'E-mail inválido.');
    const validateCPF = () => validate(cpfEl, cpfError, /^\d{11}$/.test(cpfEl.value.replace(/\D/g, '')), 'CPF precisa ter 11 números.');
    const validatePhone = () => validate(phone, phoneError, /^\d{10,11}$/.test(phone.value.replace(/\D/g, '')), 'Telefone precisa ter 10 ou 11 dígitos.');
    const validatePassword = () => {
      const isValid = validate(password, passwordError, /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{6,30}$/.test(password.value), 'Senha: 6-30 chars, maiúscula, minúscula, número e especial.');
      if (confirmPassword.value) validateConfirmPassword(); // Revalida a confirmação se a senha principal for alterada
      return isValid;
    };
    const validateConfirmPassword = () => validate(confirmPassword, confirmPasswordError, confirmPassword.value === password.value && confirmPassword.value !== '', 'As senhas não coincidem.');

    function validateBirth() {
      const v = birthEl.value;
      if (v.trim().length === 0) {
        birthError.textContent = '';
        birthEl.classList.remove('invalid', 'valid');
        return false;
      }
      if (!/^\d{2}\/\d{2}\/\d{4}$/.test(v)) return setValidationStatus(birthEl, birthError, 'Use o formato DD/MM/AAAA.');

      const [day, month, year] = v.split('/').map(Number);
      const date = new Date(year, month - 1, day);
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      let age = today.getFullYear() - date.getFullYear();
      const m = today.getMonth() - date.getMonth();
      if (m < 0 || (m === 0 && today.getDate() < date.getDate())) age--;

      if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return setValidationStatus(birthEl, birthError, 'Data inválida.');
      if (date > today) return setValidationStatus(birthEl, birthError, 'Data não pode ser no futuro.');
      if (age < 18) return setValidationStatus(birthEl, birthError, 'É necessário ter pelo menos 18 anos.');
      if (age > 120) return setValidationStatus(birthEl, birthError, 'Idade inválida.');

      return setValidationStatus(birthEl, birthError, '');
    }

    // --- Event Listeners ---
    name.addEventListener('input', validateName);
    emailEl.addEventListener('input', validateEmail);
    cpfEl.addEventListener('input', validateCPF);
    birthEl.addEventListener('blur', validateBirth);
    phone.addEventListener('input', validatePhone);
    password.addEventListener('input', validatePassword);
    confirmPassword.addEventListener('input', validateConfirmPassword);

    form.addEventListener('submit', (e) => {
      const isNameValid = validateName();
      const isEmailValid = validateEmail();
      const isCpfValid = validateCPF();
      const isBirthValid = validateBirth();
      const isPhoneValid = validatePhone();
      const isPasswordValid = validatePassword();
      const isConfirmPasswordValid = validateConfirmPassword();

      const allValid = isNameValid && isEmailValid && isCpfValid && isBirthValid && isPhoneValid && isPasswordValid && isConfirmPasswordValid;

      if (!allValid) {
        e.preventDefault(); // Apenas impede o envio se houver erros de validação no frontend.
        const firstInvalid = form.querySelector('.invalid');
        if (firstInvalid) firstInvalid.focus();
      }
    });
  }

  // --- LÓGICA DO MENU HAMBÚRGUER ---
  if (hamburgerBtn && navLinks) {
    hamburgerBtn.addEventListener('click', () => {
      navLinks.classList.toggle('active');
      // Muda o ícone para X quando aberto
      const isOpen = navLinks.classList.contains('active');
      hamburgerBtn.textContent = isOpen ? '✕' : '☰';
      hamburgerBtn.setAttribute('aria-label', isOpen ? 'Fechar menu' : 'Abrir menu');
    });
  }
  // --- LÓGICA DE MOSTRAR/OCULTAR SENHA ---
  document.querySelectorAll('.toggle-password').forEach(icon => {
    const targetId = icon.getAttribute('data-target');
    const input = document.getElementById(targetId);
    if (input) {
      const showPassword = (e) => {
        e.preventDefault(); // Evita selecionar o texto do ícone sem querer
        input.type = 'text';
        icon.textContent = '🙈';
      };
      
      const hidePassword = () => {
        input.type = 'password';
        icon.textContent = '👁️';
      };

      // Eventos de Mouse (Computador)
      icon.addEventListener('mousedown', showPassword);
      icon.addEventListener('mouseup', hidePassword);
      icon.addEventListener('mouseleave', hidePassword);

      // Eventos de Toque (Celular)
      icon.addEventListener('touchstart', showPassword);
      icon.addEventListener('touchend', hidePassword);
      icon.addEventListener('touchcancel', hidePassword);
    }
  });
});

// Limpa as senhas caso o usuário use o botão "Voltar" do navegador
window.addEventListener('pageshow', () => {
  document.querySelectorAll('.password-container input').forEach(input => {
    input.value = '';
    input.type = 'password';
  });
  document.querySelectorAll('.toggle-password').forEach(icon => icon.textContent = '👁️');
});

// INATIVIDADE (20 SEGUNDOS)
let inactivityTimeout;

function resetInactivityTimer() {
  clearTimeout(inactivityTimeout);
  // O logout automático só é ativado se o link de "Sair" estiver presente no HTML (usuário logado)
  if (document.querySelector('a[href="/logout"]')) {
    inactivityTimeout = setTimeout(() => {
      window.location.href = '/logout';
    }, 20000); // 20.000 milissegundos = 20 segundos
  }
}

// Monitora interações comuns para reiniciar o contador de inatividade
['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(eventName => {
  document.addEventListener(eventName, resetInactivityTimer, true);
});

// Inicializa o temporizador ao carregar a página ou voltar para ela
resetInactivityTimer();
