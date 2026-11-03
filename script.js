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
      title: 'Сохранять своё.',
      name: 'Лечение зубов',
      description: 'Здоровье зубов начинается с внимательного осмотра. На консультации врач оценит состояние зубов, обсудит жалобы и предложит дальнейшие шаги.',
      details: 'Лечение кариеса, восстановление повреждённого зуба и работа с корневыми каналами обсуждаются по показаниям. Доступность процедуры и стоимость уточняйте в клинике.'
    },
    aesthetic: {
      title: 'Комфорт в каждом движении.',
      name: 'Восстановление функции зубов',
      description: 'Повреждённые зубы могут мешать привычно жевать и говорить. На консультации врач оценит их состояние и обсудит варианты восстановления.',
      details: 'Необходимость коронок, вкладок или мостовидных протезов определяется после обследования. Метод и материалы подбираются индивидуально.'
    },
    restore: {
      title: 'Снова быть собой.',
      name: 'Имплантация зубов',
      description: 'Когда зуб повреждён или утрачен, важно рассмотреть не только эстетику, но и функцию. Начните с обсуждения вашей ситуации с врачом.',
      details: 'Способ восстановления, необходимость хирургического этапа и доступные варианты протезирования уточняются в клинике. Сроки и стоимость зависят от плана лечения.'
    },
    hygiene: {
      title: 'Забота на каждый день.',
      name: 'Гигиена и профилактика',
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

  function showInfo({ eyebrow, title, description, details, policy = false }) {
    document.querySelector('#info-eyebrow').textContent = eyebrow;
    document.querySelector('#info-title').textContent = title;
    document.querySelector('#info-description').textContent = description;
    document.querySelector('#info-details').textContent = details;
    const appointmentLink = document.querySelector('#info-appointment');
    appointmentLink.hidden = policy;
    openDialog(infoDialog);
  }

  document.querySelectorAll('[data-service]').forEach(button => {
    button.addEventListener('click', () => {
      const service = services[button.dataset.service];
      showInfo({ eyebrow: service.name.toLocaleUpperCase('ru-RU'), title: service.title, description: service.description, details: service.details });
    });
  });
  document.querySelectorAll('[data-doctor]').forEach(button => {
    button.addEventListener('click', () => {
      const doctor = doctors[button.dataset.doctor];
      showInfo({ eyebrow: doctor.role, title: doctor.title, description: doctor.description, details: doctor.details });
    });
  });
  document.querySelector('#info-appointment').addEventListener('click', () => infoDialog.close());
  document.querySelectorAll('[data-policy]').forEach(button => {
    button.addEventListener('click', () => showInfo({
      eyebrow: 'КОНФИДЕНЦИАЛЬНОСТЬ',
      title: 'Ваши данные - под вашим контролем.',
      description: 'Форма работает в режиме предпросмотра: введённые имя и телефон остаются только на этой странице до её перезагрузки. Сайт не отправляет их в клинику. Для записи позвоните нам.',
      details: 'Сайт не сохраняет контакты в локальном хранилище браузера. Встроенная карта загружается с сервиса Яндекс.Карты; при её загрузке браузер обращается к этому сервису. Внешние ссылки открывают сторонние сайты. Для связи с клиникой: +7 950 949-93-25.',
      policy: true
    }));
  });

  const appointmentForm = document.querySelector('#appointment-form');
  const appointmentFields = [...appointmentForm.querySelectorAll('input[required]')];
  const appointmentStatus = document.querySelector('#appointment-status');
  let appointmentAttempted = false;
  function validateAppointmentField(field) {
    let message = '';
    if (field.id === 'appointment-name' && (!field.value.trim() || !field.validity.valid)) message = 'Укажите ваше имя.';
    else if (!field.validity.valid) {
      if (field.type === 'checkbox') message = 'Подтвердите согласие на обработку данных.';
      else if (field.validity.valueMissing) message = 'Укажите номер телефона.';
      else message = 'Введите от 10 до 15 цифр, с кодом страны.';
    }
    const error = document.querySelector('#' + field.id + '-error');
    error.textContent = message;
    error.hidden = !message;
    field.setAttribute('aria-invalid', String(Boolean(message)));
    return !message;
  }
  appointmentFields.forEach(field => {
    field.addEventListener(field.type === 'checkbox' ? 'change' : 'input', () => {
      if (appointmentAttempted) validateAppointmentField(field);
      appointmentStatus.textContent = '';
    });
  });
  appointmentForm.addEventListener('submit', event => {
    event.preventDefault();
    appointmentAttempted = true;
    appointmentStatus.textContent = '';
    const invalidFields = appointmentFields.filter(field => !validateAppointmentField(field));
    if (invalidFields.length) {
      invalidFields[0].focus();
      return;
    }
    appointmentStatus.textContent = 'Отправка пока недоступна. Позвоните в клинику: +7 950 949-93-25.';
  });
  appointmentForm.noValidate = true;
  document.querySelector('#appointment-submit').hidden = false;

  const techDetails = [...document.querySelectorAll('[data-tech]')];
  techDetails.forEach(detail => detail.addEventListener('toggle', () => {
    if (!detail.open) return;
    techDetails.forEach(other => {
      if (other !== detail) other.open = false;
    });
  }));

  const comparisonRange = document.querySelector('#smile-comparison');
  comparisonRange.hidden = false;
  comparisonRange.addEventListener('input', () => {
    comparisonRange.parentElement.style.setProperty('--reveal', comparisonRange.value + '%');
  });

  const reviewTrack = document.querySelector('.review-track');
  const reviewCards = [...reviewTrack.children];
  let reviewIndex = 0;
  function selectReview(index) {
    reviewIndex = (index + reviewCards.length) % reviewCards.length;
    const target = reviewCards[reviewIndex];
    reviewTrack.scrollTo({ left: target.offsetLeft - reviewCards[0].offsetLeft, behavior: reducedMotion.matches ? 'instant' : 'smooth' });
    document.querySelector('#review-current').textContent = String(reviewIndex + 1).padStart(2, '0');
    document.querySelector('.review-position-line').style.setProperty('--progress', reviewIndex * 50 + '%');
  }
  document.querySelector('#review-prev').addEventListener('click', () => selectReview(reviewIndex - 1));
  document.querySelector('#review-next').addEventListener('click', () => selectReview(reviewIndex + 1));
  reviewTrack.addEventListener('scroll', () => {
    if (reviewTrack.scrollWidth <= reviewTrack.clientWidth + 1) return;
    const nextIndex = reviewTrack.scrollLeft > (reviewTrack.scrollWidth - reviewTrack.clientWidth) / 2 ? 1 : 0;
    document.querySelector('#review-current').textContent = String(nextIndex + 1).padStart(2, '0');
    document.querySelector('.review-position-line').style.setProperty('--progress', nextIndex * 50 + '%');
    reviewIndex = nextIndex;
  }, { passive: true });

  if ('IntersectionObserver' in window && !reducedMotion.matches) {
    const revealObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.remove('reveal-pending');
        revealObserver.unobserve(entry.target);
      });
    }, { threshold: .08 });
    document.querySelectorAll('.reveal').forEach(element => {
      element.classList.add('reveal-pending');
      revealObserver.observe(element);
    });
  }

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

  const parallaxImage = document.querySelector('[data-parallax]');
  let scrollPending = false;
  function renderScroll() {
    header.classList.toggle('scrolled', window.scrollY > 20);
    if (!reducedMotion.matches && window.scrollY < 1100) parallaxImage.style.transform = 'translateY(' + Math.min(window.scrollY * .075, 65) + 'px)';
    scrollPending = false;
  }
  window.addEventListener('scroll', () => {
    if (scrollPending) return;
    scrollPending = true;
    window.requestAnimationFrame(renderScroll);
  }, { passive: true });
  reducedMotion.addEventListener('change', () => {
    if (reducedMotion.matches) parallaxImage.style.transform = '';
  });
  renderScroll();
  document.querySelector('#year').textContent = new Date().getFullYear();
})();
