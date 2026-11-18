(() => {
  'use strict';

  document.documentElement.classList.add('js');

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const header = document.querySelector('.header');
  const menuToggle = document.querySelector('.menu-toggle');
  const navigation = document.querySelector('#navigation');
  const infoDialog = document.querySelector('#info-dialog');

  const services = {
    therapy: {
      title: 'Лечение зубов',
      description: 'Здоровье зубов начинается с внимательного осмотра. На консультации врач оценит состояние зубов, обсудит жалобы и предложит дальнейшие шаги.',
      details: 'Лечение кариеса, восстановление повреждённого зуба и работа с корневыми каналами обсуждаются по показаниям. Доступность процедуры и стоимость уточняйте в клинике.'
    },
    aesthetic: {
      title: 'Восстановление функции зубов',
      description: 'Повреждённые зубы могут мешать привычно жевать и говорить. На консультации врач оценит их состояние и обсудит варианты восстановления.',
      details: 'Необходимость коронок, вкладок или мостовидных протезов определяется после обследования. Метод и материалы подбираются индивидуально.'
    },
    restore: {
      title: 'Имплантация зубов',
      description: 'Когда зуб повреждён или утрачен, важно рассмотреть не только эстетику, но и функцию. Начните с обсуждения вашей ситуации с врачом.',
      details: 'Способ восстановления, необходимость хирургического этапа и доступные варианты протезирования уточняются в клинике. Сроки и стоимость зависят от плана лечения.'
    },
    hygiene: {
      title: 'Гигиена и профилактика',
      description: 'Профессиональный уход дополняет домашнюю гигиену. Врач оценит состояние зубов и дёсен и поможет разобраться в ежедневном уходе.',
      details: 'Состав профессиональной гигиены и периодичность посещений подбираются индивидуально. На консультации можно обсудить выбор щётки, пасты и дополнительных средств.'
    }
  };

  const doctors = {
    kamol: {
      title: 'Камол Акмалович Сайдазимов',
      role: 'СТОМАТОЛОГ · СТОМАТОЛОГ-ОРТОПЕД',
      description: 'Эстетика, восстановление зубов и ортопедическое лечение. Выпускник Казанского государственного медицинского университета, 2023 год.',
      details: 'На консультации можно обсудить состояние зубов, эстетические пожелания и возможные варианты восстановления. Время приёма уточняйте по телефону клиники.'
    },
    dzhamal: {
      title: 'Джамал Акмалович Сайдазимов',
      role: 'СТОМАТОЛОГ-ХИРУРГ',
      description: 'Хирургическая стоматология. Выпускник Казанского государственного медицинского университета, 2021 год. Образование по хирургической стоматологии - 2023 год.',
      details: 'Врач обсудит вашу ситуацию и возможные варианты хирургического лечения. Объём вмешательства определяется после обследования. Актуальное расписание уточняйте в клинике.'
    },
    milena: {
      title: 'Милена Радиковна Шакирьянова',
      role: 'СТОМАТОЛОГ-ОРТОДОНТ · СТОМАТОЛОГ',
      description: 'Ортодонтия и лечение зубов. Выпускница Казанского государственного медицинского университета по специальности «Стоматология», 2021 год.',
      details: 'Прошла повышение квалификации по эндодонтии, реставрации зубов, КЛКТ и диагностике на ортодонтическом приёме. Актуальное расписание и запись уточняйте в клинике.'
    }
  };

  function setMenu(open) {
    menuToggle.setAttribute('aria-expanded', String(open));
    menuToggle.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    navigation.classList.toggle('is-open', open);
    document.body.classList.toggle('menu-open', open);
    document.querySelector('main').inert = open;
    document.querySelector('footer').inert = open;
  }

  menuToggle.addEventListener('click', () => setMenu(menuToggle.getAttribute('aria-expanded') !== 'true'));
  header.addEventListener('click', event => {
    if (event.target.closest('a')) setMenu(false);
  });
  document.addEventListener('keydown', event => {
    if (menuToggle.getAttribute('aria-expanded') !== 'true') return;
    if (event.key === 'Escape') {
      setMenu(false);
      menuToggle.focus();
    }
    if (event.key === 'Tab') {
      const focusable = [...document.querySelectorAll('.header a, .header button')].filter(element => element.getClientRects().length);
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
  window.matchMedia('(min-width: 901px)').addEventListener('change', event => {
    if (event.matches) setMenu(false);
  });

  function openDialog(dialog) {
    setMenu(false);
    dialog.showModal();
    document.body.classList.add('dialog-open');
  }

  document.querySelectorAll('dialog').forEach(dialog => {
    dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    });
    dialog.addEventListener('close', () => {
      document.body.classList.remove('dialog-open');
    });
  });

  function showInfo({ eyebrow, title, description, details }) {
    document.querySelector('#info-eyebrow').textContent = eyebrow;
    document.querySelector('#info-title').textContent = title;
    document.querySelector('#info-description').textContent = description;
    document.querySelector('#info-details').textContent = details;
    openDialog(infoDialog);
  }

  document.querySelectorAll('[data-service]').forEach(button => {
    button.addEventListener('click', () => {
      const service = services[button.dataset.service];
      showInfo({ eyebrow: '', title: service.title, description: service.description, details: service.details });
    });
  });
  document.querySelectorAll('[data-doctor]').forEach(button => {
    button.addEventListener('click', () => {
      const doctor = doctors[button.dataset.doctor];
      showInfo({ eyebrow: doctor.role, title: doctor.title, description: doctor.description, details: doctor.details });
    });
  });
  document.querySelector('#info-appointment').addEventListener('click', () => infoDialog.close());
  const cookieNotice = document.querySelector('#cookie-notice');
  try {
    cookieNotice.hidden = document.cookie.split(';').some(cookie => cookie.trim() === 'saydent_cookie_notice=1');
  } catch {
    cookieNotice.hidden = false;
  }
  document.querySelector('#cookie-dismiss').addEventListener('click', () => {
    try {
      document.cookie = 'saydent_cookie_notice=1; Max-Age=15552000; Path=/; SameSite=Lax' + (window.location.protocol === 'https:' ? '; Secure' : '');
    } catch {
      // Cookie restrictions must not prevent closing the notice.
    }
    cookieNotice.hidden = true;
  });

  const appointmentForm = document.querySelector('#appointment-form');
  const appointmentFields = [...appointmentForm.querySelectorAll('input[required]')];
  const appointmentStatus = document.querySelector('#appointment-status');
  let appointmentAttempted = false;
  let submissionUntil = 0;
  let pendingRequest = null;
  const submitButton = document.querySelector('#appointment-submit');
  function validateAppointmentField(field) {
    let message = '';
    if (field.id === 'appointment-name' && (!field.value.trim() || /\p{Nd}/u.test(field.value) || !field.validity.valid)) message = /\p{Nd}/u.test(field.value) ? 'Укажите имя без цифр.' : 'Укажите ваше имя.';
    else if (!field.validity.valid) {
      if (field.type === 'checkbox') message = 'Подтвердите согласие.';
      else if (field.validity.valueMissing) message = 'Укажите номер телефона.';
      else message = 'Нужно от 10 до 15 цифр.';
    }
    const error = document.querySelector('#' + field.id + '-error');
    error.textContent = message;
    error.hidden = !message;
    field.setAttribute('aria-invalid', String(Boolean(message)));
    return !message;
  }
  appointmentFields.forEach(field => {
    field.addEventListener(field.type === 'checkbox' ? 'change' : 'input', () => {
      if (field.id === 'appointment-name' || field.type === 'tel') {
        const cleanValue = value => field.type === 'tel'
          ? value.replace(/[^0-9+ ()-]/g, '').replace(/(?!^)\+/g, '')
          : value.replace(/\p{Nd}/gu, '');
        const cleaned = cleanValue(field.value);
        if (cleaned !== field.value) {
          const start = cleanValue(field.value.slice(0, field.selectionStart)).length;
          const end = cleanValue(field.value.slice(0, field.selectionEnd)).length;
          field.value = cleaned;
          field.setSelectionRange(start, end);
        }
      }
      if (appointmentAttempted) validateAppointmentField(field);
      appointmentStatus.textContent = '';
    });
  });
  appointmentForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (submitButton.disabled) return;
    appointmentAttempted = true;
    appointmentStatus.textContent = '';
    const invalidFields = appointmentFields.filter(field => !validateAppointmentField(field));
    if (invalidFields.length) {
      invalidFields[0].focus();
      return;
    }
    let alreadySubmitted = Date.now() < submissionUntil;
    try {
      alreadySubmitted ||= document.cookie.split(';').some(cookie => cookie.trim() === 'saydent_submitted=1');
    } catch {
      // Keep the current-page limit even when cookies are blocked.
    }
    if (alreadySubmitted) {
      appointmentStatus.textContent = 'Вы уже заполнили форму. Для подтверждения записи позвоните: +7 950 949-93-25.';
      return;
    }
    const payload = {
      name: appointmentFields[0].value.trim(),
      phone: appointmentFields[1].value,
      consent: appointmentFields[2].checked,
      consent_version: '2026-11-18'
    };
    const fingerprint = JSON.stringify(payload);
    if (!pendingRequest || pendingRequest.fingerprint !== fingerprint) {
      pendingRequest = { fingerprint, id: window.crypto.randomUUID() };
    }
    submitButton.disabled = true;
    appointmentStatus.textContent = 'Отправляем заявку…';
    try {
      const response = await fetch('/api/appointments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, request_id: pendingRequest.id }),
        signal: typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function'
          ? AbortSignal.timeout(15000) : undefined
      });
      const result = await response.json();
      if (!response.ok || result.ok !== true) throw new Error(result.message || 'Не удалось отправить заявку.');
      pendingRequest = null;
      submissionUntil = Date.now() + 10 * 60 * 1000;
      try {
        document.cookie = 'saydent_submitted=1; Max-Age=600; Path=/; SameSite=Lax' + (window.location.protocol === 'https:' ? '; Secure' : '');
      } catch {
        // The server also limits duplicate submissions when cookies are blocked.
      }
      document.querySelector('#appointment-receipt').hidden = false;
      document.querySelector('#receipt-title').focus({ preventScroll: true });
    } catch (error) {
      appointmentStatus.textContent = error.name === 'TypeError' || error.name === 'TimeoutError' || error.name === 'SyntaxError'
        ? 'Не удалось подтвердить отправку. Повторите заявку или позвоните: +7 950 949-93-25.'
        : error.message;
    } finally {
      submitButton.disabled = false;
    }
  });
  appointmentForm.noValidate = true;
  document.querySelector('#appointment-submit').hidden = false;

  const techDetails = [...document.querySelectorAll('[data-tech]')];
  const priceDetails = [...document.querySelectorAll('.price-accordion details')];
  [techDetails, priceDetails].forEach(details => {
    details.forEach(detail => {
      const summary = detail.querySelector('summary');
      summary.addEventListener('click', event => {
        event.preventDefault();
        const opening = !detail.open;
        details.forEach(other => { other.open = other === detail && opening; });
        if (opening && details === priceDetails) summary.scrollIntoView({ block: 'start', behavior: 'instant' });
      });
    });
  });

  const comparisonRange = document.querySelector('#smile-comparison');
  comparisonRange.hidden = false;
  comparisonRange.addEventListener('input', () => {
    comparisonRange.parentElement.style.setProperty('--reveal', comparisonRange.value + '%');
  });

  const reviewTrack = document.querySelector('.review-track');
  const reviewCards = [...reviewTrack.children];
  let reviewIndex = 0;
  function updateReviewPosition(index) {
    reviewIndex = index;
    document.querySelector('#review-current').textContent = String(index + 1).padStart(2, '0');
    document.querySelector('.review-position-line').style.setProperty('--progress', index / Math.max(1, reviewCards.length - 1) * 50 + '%');
  }
  function selectReview(index) {
    updateReviewPosition((index + reviewCards.length) % reviewCards.length);
    const target = reviewCards[reviewIndex];
    reviewTrack.scrollTo({ left: target.offsetLeft - reviewCards[0].offsetLeft, behavior: reducedMotion.matches ? 'instant' : 'smooth' });
  }
  document.querySelector('#review-prev').addEventListener('click', () => selectReview(reviewIndex - 1));
  document.querySelector('#review-next').addEventListener('click', () => selectReview(reviewIndex + 1));
  reviewTrack.addEventListener('scroll', () => {
    if (reviewTrack.scrollWidth <= reviewTrack.clientWidth + 1) return;
    const maxScroll = reviewTrack.scrollWidth - reviewTrack.clientWidth;
    const distance = card => Math.abs(reviewTrack.scrollLeft - Math.min(card.offsetLeft - reviewCards[0].offsetLeft, maxScroll));
    const nextIndex = reviewCards.reduce((nearest, card, index) => distance(card) < distance(reviewCards[nearest]) ? index : nearest, 0);
    updateReviewPosition(nextIndex);
  }, { passive: true });

  if ('IntersectionObserver' in window) {
    const links = [...navigation.querySelectorAll('a')];
    const sectionObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        links.forEach(link => {
          if (link.hash === '#' + entry.target.id) link.setAttribute('aria-current', 'location');
          else link.removeAttribute('aria-current');
        });
      });
    }, { rootMargin: '-15% 0px -55% 0px', threshold: 0 });
    document.querySelectorAll('main > section[id]').forEach(section => sectionObserver.observe(section));
  }

  let scrollPending = false;
  function renderScroll() {
    header.classList.toggle('scrolled', window.scrollY > 20);
    scrollPending = false;
  }
  window.addEventListener('scroll', () => {
    if (scrollPending) return;
    scrollPending = true;
    window.requestAnimationFrame(renderScroll);
  }, { passive: true });
  renderScroll();
  document.querySelector('#year').textContent = new Date().getFullYear();
})();
