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
  const selectedImage = selectedPanel.querySelector('.gallery-selected-image img');
  const numbers = selectedPanel.querySelector('.gallery-selected-numbers');
  const thumbnails = selectedPanel.querySelector('[data-action="thumbnails"]');
  let selected = -1;
  let columns = 0;

  const renderSelection = (index) => {
    selected = ((index % photos.length) + photos.length) % photos.length;
    const current = photos[selected].querySelector('img');
    selectedImage.src = current.src;
    selectedImage.alt = current.alt;
    photos.forEach((photo, i) => photo.classList.toggle('is-selected', i === selected));
    numbers.querySelectorAll('button').forEach((button, i) => {
      button.setAttribute('aria-current', i === selected ? 'page' : 'false');
    });
    selectedPanel.hidden = false;
    gallery.hidden = true;
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
    photo.addEventListener('click', () => renderSelection(i));
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = i + 1;
    button.addEventListener('click', () => renderSelection(i));
    numbers.append(button);
  });

  thumbnails.addEventListener('click', showThumbnails);
  window.addEventListener('resize', layout);

  Promise.all(photos.map((photo) => photo.querySelector('img').decode().catch(() => {}))).then(() => {
    columns = 0;
    layout();
  });
  layout();
})();
