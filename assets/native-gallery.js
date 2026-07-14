(() => {
  const gallery = document.querySelector('.gallery-columns');
  const photos = [...document.querySelectorAll('.photo')];
  const viewer = document.querySelector('.viewer');
  const viewerImage = document.querySelector('.viewer-image img');
  const numbers = document.querySelector('.viewer-numbers');
  let selected = -1, columns = 0;

  const photoFromHash = () => {
    const match = location.hash.match(/^#photo-(\d+)$/);
    return match ? Number(match[1]) - 1 : -1;
  };
  const change = (index, history) => {
    selected = ((index % photos.length) + photos.length) % photos.length;
    viewerImage.src = photos[selected].querySelector('img').src;
    viewerImage.alt = photos[selected].querySelector('img').alt;
    viewer.classList.add('is-open');
    numbers.querySelectorAll('button').forEach((button, i) => button.setAttribute('aria-current', i === selected));
    if (history) window.history.pushState({ photo: selected }, '', `#photo-${selected + 1}`);
  };
  const thumbnails = () => {
    selected = -1;
    viewer.classList.remove('is-open');
    if (location.hash) window.history.replaceState({}, '', location.pathname + location.search);
  };
  const layout = () => {
    const count = Math.max(1, Math.floor((gallery.clientWidth + 14) / 444));
    if (count === columns) return;
    columns = count;
    gallery.style.setProperty('--gallery-columns', count);
    const heights = Array(count).fill(0);
    const containers = heights.map(() => document.createElement('div'));
    containers.forEach(column => column.className = 'gallery-column');
    photos.forEach(photo => {
      const image = photo.querySelector('img');
      const height = image.naturalWidth ? image.naturalHeight / image.naturalWidth : 1;
      const target = heights.indexOf(Math.min(...heights));
      containers[target].append(photo);
      heights[target] += height;
    });
    gallery.replaceChildren(...containers);
  };

  photos.forEach((photo, i) => photo.addEventListener('click', () => change(i, true)));
  photos.forEach((_, i) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = i + 1;
    button.setAttribute('aria-label', `Photo ${i + 1}`);
    button.addEventListener('click', () => change(i, true));
    numbers.append(button);
  });
  document.querySelector('[data-action="previous"]').addEventListener('click', () => change(selected - 1, true));
  document.querySelector('[data-action="next"]').addEventListener('click', () => change(selected + 1, true));
  document.querySelector('[data-action="thumbnails"]').addEventListener('click', thumbnails);
  window.addEventListener('keydown', event => {
    if (selected < 0) return;
    if (event.key === 'Escape') thumbnails();
    if (event.key === 'ArrowLeft') change(selected - 1, true);
    if (event.key === 'ArrowRight') change(selected + 1, true);
  });
  window.addEventListener('popstate', () => {
    const photo = photoFromHash();
    photo < 0 ? thumbnails() : change(photo, false);
  });
  window.addEventListener('resize', layout);
  Promise.all(photos.map(photo => photo.querySelector('img').decode().catch(() => {}))).then(() => {
    columns = 0;
    layout();
  });
  layout();
  const initial = photoFromHash();
  if (initial >= 0 && initial < photos.length) change(initial, false);
  const menu = document.querySelector('.menu-toggle');
  menu.addEventListener('click', () => {
    const open = document.querySelector('.site-nav').classList.toggle('is-open');
    menu.setAttribute('aria-expanded', open);
  });
})();
