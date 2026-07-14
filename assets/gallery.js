(() => {
  const menu = document.querySelector('.menu-toggle');
  if (menu) {
    menu.addEventListener('click', () => {
      const nav = document.querySelector('.site-nav');
      const open = nav.classList.toggle('is-open');
      menu.setAttribute('aria-expanded', String(open));
    });
  }

  const gallery = document.querySelector('.gallery-columns');
  const selectedPanel = document.querySelector('.gallery-selected');
  if (!gallery || !selectedPanel) return;

  const photos = [...document.querySelectorAll('.photo')];
  const selectedFigure = selectedPanel.querySelector('.gallery-selected-image');
  const selectedImage = selectedPanel.querySelector('.gallery-selected-image img');
  const numbers = selectedPanel.querySelector('.gallery-selected-numbers');
  const thumbnails = selectedPanel.querySelector('[data-action="thumbnails"]');
  const previousZone = selectedPanel.querySelector('[data-action="previous-photo"]');
  const nextZone = selectedPanel.querySelector('[data-action="next-photo"]');
  const cursorSample = document.createElement('canvas');
  const cursorContext = cursorSample.getContext('2d', { willReadFrequently: true });
  let selected = -1;
  let columns = 0;
  cursorSample.width = 1;
  cursorSample.height = 1;
  const cursor = (path, color, fallback) =>
    `url("data:image/svg+xml,${encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18"><path d="${path}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`
    )}") 9 9, ${fallback}`;
  const arrowCursors = {
    previous: {
      dark: cursor('M11.5 3 5.5 9l6 6', '#fff', 'w-resize'),
      light: cursor('M11.5 3 5.5 9l6 6', '#555', 'w-resize'),
    },
    next: {
      dark: cursor('M6.5 3 12.5 9l-6 6', '#fff', 'e-resize'),
      light: cursor('M6.5 3 12.5 9l-6 6', '#555', 'e-resize'),
    },
  };

  const reveal = (image) => image.decode().catch(() => {}).finally(() => image.classList.add('is-loaded'));

  const sizeSelection = (image = selectedImage) => {
    if (selected < 0 || !image.naturalWidth) return;
    if (window.matchMedia('(max-width: 699px)').matches) {
      selectedFigure.style.width = '';
      selectedFigure.style.height = '';
      return;
    }
    const ratio = image.naturalWidth / image.naturalHeight;
    const width = Math.min(window.innerWidth - 233, (window.innerHeight - 46) * ratio);
    selectedFigure.style.width = `${Math.max(1, width)}px`;
    selectedFigure.style.height = `${Math.max(1, width / ratio)}px`;
  };

  const renderSelection = (index) => {
    selected = ((index % photos.length) + photos.length) % photos.length;
    const current = photos[selected].querySelector('img');
    selectedImage.src = current.src;
    selectedImage.alt = current.alt;
    selectedFigure.dataset.cursorTone = 'dark';
    previousZone.style.cursor = '';
    nextZone.style.cursor = '';
    sizeSelection(current);
    selectedImage.decode().catch(() => {}).finally(() => sizeSelection());
    photos.forEach((photo, i) => photo.classList.toggle('is-selected', i === selected));
    numbers.querySelectorAll('button').forEach((button, i) => {
      button.setAttribute('aria-current', i === selected ? 'page' : 'false');
    });
    selectedPanel.hidden = false;
    gallery.hidden = true;
  };

  const updateCursorTone = (event) => {
    if (!selectedImage.naturalWidth || !cursorContext) return;
    const rect = selectedImage.getBoundingClientRect();
    const x = Math.min(selectedImage.naturalWidth - 1, Math.max(0, Math.floor(((event.clientX - rect.left) / rect.width) * selectedImage.naturalWidth)));
    const y = Math.min(selectedImage.naturalHeight - 1, Math.max(0, Math.floor(((event.clientY - rect.top) / rect.height) * selectedImage.naturalHeight)));
    try {
      cursorContext.drawImage(selectedImage, x, y, 1, 1, 0, 0, 1, 1);
      const [r, g, b] = cursorContext.getImageData(0, 0, 1, 1).data;
      const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      const tone = luminance >= 128 ? 'light' : 'dark';
      selectedFigure.dataset.cursorTone = tone;
      event.currentTarget.style.cursor = arrowCursors[event.currentTarget === previousZone ? 'previous' : 'next'][tone];
    } catch {
      selectedFigure.dataset.cursorTone = 'dark';
      event.currentTarget.style.cursor = arrowCursors[event.currentTarget === previousZone ? 'previous' : 'next'].dark;
    }
  };

  const showThumbnails = () => {
    selected = -1;
    selectedPanel.hidden = true;
    gallery.hidden = false;
    photos.forEach((photo) => photo.classList.remove('is-selected'));
  };

  const layout = () => {
    const count = Math.max(1, Math.floor((gallery.clientWidth + 14) / 444));
    if (count === columns) return;
    columns = count;
    gallery.style.setProperty('--gallery-columns', count);
    const heights = Array(count).fill(0);
    const containers = heights.map(() => {
      const column = document.createElement('div');
      column.className = 'gallery-column';
      return column;
    });
    photos.forEach((photo) => {
      const image = photo.querySelector('img');
      const height = image.naturalWidth ? image.naturalHeight / image.naturalWidth : 1;
      const target = heights.indexOf(Math.min(...heights));
      containers[target].append(photo);
      heights[target] += height;
    });
    gallery.replaceChildren(...containers);
  };

  photos.forEach((photo, i) => {
    reveal(photo.querySelector('img'));
    photo.addEventListener('click', () => renderSelection(i));
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = i + 1;
    button.addEventListener('click', () => renderSelection(i));
    numbers.append(button);
  });

  thumbnails.addEventListener('click', showThumbnails);
  previousZone.addEventListener('click', () => renderSelection(selected - 1));
  nextZone.addEventListener('click', () => renderSelection(selected + 1));
  previousZone.addEventListener('pointermove', updateCursorTone);
  nextZone.addEventListener('pointermove', updateCursorTone);
  window.addEventListener('keydown', (event) => {
    if (selectedPanel.hidden) return;
    if (selected < 0) return;
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      renderSelection(selected - 1);
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      renderSelection(selected + 1);
    }
  });
  window.addEventListener('resize', () => {
    layout();
    sizeSelection();
  });

  Promise.all(photos.map((photo) => photo.querySelector('img').decode().catch(() => {}))).then(() => {
    columns = 0;
    layout();
  });
  layout();
})();
