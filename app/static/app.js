let currentDocumentId = null;
let currentFilename = null;
let currentPageCount = 0;
const pagesToDelete = new Set();

const priorPdf = document.getElementById('priorPdf');
const uploadPrior = document.getElementById('uploadPrior');
const priorStatus = document.getElementById('priorStatus');
const thumbnailGrid = document.getElementById('thumbnailGrid');
const createBackup = document.getElementById('createBackup');
const createStatus = document.getElementById('createStatus');
const incomeTaxSeason = document.getElementById('incomeTaxSeason');
const seasonSummary = document.getElementById('seasonSummary');
const taxYear = document.getElementById('taxYear');
const clientFilename = document.getElementById('clientFilename');
const newPdfs = document.getElementById('newPdfs');
const sharedYear = document.getElementById('sharedYear');
const sharedQuery = document.getElementById('sharedQuery');
const searchShared = document.getElementById('searchShared');
const sharedResults = document.getElementById('sharedResults');
const previewModal = document.getElementById('previewModal');
const previewImage = document.getElementById('previewImage');
const previewTitle = document.getElementById('previewTitle');
const closePreview = document.getElementById('closePreview');

function setStatus(element, text, isError = false) {
  element.textContent = text;
  element.classList.toggle('error', isError);
}

function currentSeason() {
  return incomeTaxSeason.value.trim();
}

function backupYearForSeason(season) {
  return String(Number.parseInt(season, 10) - 1);
}

function syncSeasonFields({ clearResults = false } = {}) {
  const season = currentSeason();
  const backupYear = backupYearForSeason(season);
  sharedYear.value = backupYear;
  taxYear.value = season;
  seasonSummary.textContent = `${season} season: search ${backupYear} backup folder, then save final PDF into ${season} folder.`;
  if (clearResults) {
    sharedResults.innerHTML = '';
  }
}

function clearActiveDocument() {
  currentDocumentId = null;
  currentFilename = null;
  currentPageCount = 0;
  pagesToDelete.clear();
  thumbnailGrid.innerHTML = '';
}

function pageImageUrl(page) {
  return `/api/prior-pdf/${currentDocumentId}/thumbnail/${page}`;
}

function keptPages() {
  const pages = [];
  for (let page = 1; page <= currentPageCount; page += 1) {
    if (!pagesToDelete.has(page)) {
      pages.push(page);
    }
  }
  return pages;
}

function openPreview(page) {
  if (!currentDocumentId) {
    return;
  }
  previewTitle.textContent = `Page ${page} Preview`;
  previewImage.src = pageImageUrl(page);
  previewImage.alt = `Large preview of page ${page}`;
  previewModal.hidden = false;
}

function hidePreview() {
  previewModal.hidden = true;
  previewImage.removeAttribute('src');
}

function updateDeleteButton(card, deleteButton, page) {
  const marked = pagesToDelete.has(page);
  card.classList.toggle('marked-delete', marked);
  deleteButton.textContent = marked ? 'Marked Delete' : 'Mark Delete';
  deleteButton.setAttribute('aria-pressed', String(marked));
}

function renderThumbnails(pageCount) {
  thumbnailGrid.innerHTML = '';
  pagesToDelete.clear();
  currentPageCount = pageCount;

  for (let page = 1; page <= pageCount; page += 1) {
    const card = document.createElement('article');
    card.className = 'thumb';
    card.dataset.page = String(page);

    const img = document.createElement('img');
    img.alt = `Page ${page}`;
    img.src = pageImageUrl(page);

    const label = document.createElement('span');
    label.className = 'page-label';
    label.textContent = `Page ${page}`;

    const actions = document.createElement('div');
    actions.className = 'thumb-actions';

    const previewButton = document.createElement('button');
    previewButton.type = 'button';
    previewButton.className = 'secondary-button';
    previewButton.textContent = 'Preview';
    previewButton.addEventListener('click', () => openPreview(page));

    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.className = 'delete-button';
    deleteButton.textContent = 'Mark Delete';
    deleteButton.addEventListener('click', () => {
      if (pagesToDelete.has(page)) {
        pagesToDelete.delete(page);
      } else {
        pagesToDelete.add(page);
      }
      updateDeleteButton(card, deleteButton, page);
    });

    actions.appendChild(previewButton);
    actions.appendChild(deleteButton);
    card.appendChild(img);
    card.appendChild(label);
    card.appendChild(actions);
    thumbnailGrid.appendChild(card);
  }
}

function activateDocument(payload, sourceLabel) {
  currentDocumentId = payload.document_id;
  currentFilename = payload.filename;
  if (!clientFilename.value) {
    clientFilename.value = currentFilename;
  }
  setStatus(priorStatus, `${sourceLabel}: ${payload.filename} with ${payload.page_count} pages.`);
  renderThumbnails(payload.page_count);
}

async function openSharedPdf(relativePath) {
  const form = new FormData();
  form.append('relative_path', relativePath);
  setStatus(priorStatus, 'Opening shared PDF...');

  const response = await fetch('/api/shared/prior-pdf', { method: 'POST', body: form });
  if (!response.ok) {
    setStatus(priorStatus, await response.text(), true);
    return;
  }

  activateDocument(await response.json(), 'Opened from shared folder');
}

searchShared.addEventListener('click', async () => {
  sharedResults.innerHTML = '';
  syncSeasonFields({ clearResults: true });
  const params = new URLSearchParams({
    year: sharedYear.value.trim(),
    query: sharedQuery.value.trim(),
  });
  setStatus(priorStatus, 'Searching shared folder...');

  const response = await fetch(`/api/shared/prior-pdfs?${params}`);
  if (!response.ok) {
    setStatus(priorStatus, 'Shared folder is not configured yet. Use upload demo mode for now.', true);
    return;
  }

  const payload = await response.json();
  if (!payload.results.length) {
    setStatus(priorStatus, `No PDFs found in ${sharedYear.value}.`, true);
    return;
  }

  setStatus(priorStatus, `Found ${payload.results.length} PDF(s) in ${payload.document_root}.`);
  for (const result of payload.results) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'result-row';
    button.textContent = result.relative_path;
    button.addEventListener('click', () => openSharedPdf(result.relative_path));
    sharedResults.appendChild(button);
  }
});

uploadPrior.addEventListener('click', async () => {
  if (!priorPdf.files.length) {
    setStatus(priorStatus, 'Select a prior-year PDF first.', true);
    return;
  }

  const form = new FormData();
  form.append('file', priorPdf.files[0]);
  setStatus(priorStatus, 'Uploading and reading PDF...');

  const response = await fetch('/api/prior-pdf', { method: 'POST', body: form });
  if (!response.ok) {
    setStatus(priorStatus, await response.text(), true);
    return;
  }

  activateDocument(await response.json(), 'Opened uploaded PDF');
});

createBackup.addEventListener('click', async () => {
  if (!currentDocumentId) {
    setStatus(createStatus, 'Open a prior-year PDF first.', true);
    return;
  }

  const pages = keptPages();
  if (!pages.length) {
    setStatus(createStatus, 'At least one prior-year page must remain. Unmark one page before creating the backup.', true);
    return;
  }

  const form = new FormData();
  form.append('document_id', currentDocumentId);
  form.append('selected_pages', pages.join(','));
  syncSeasonFields();
  form.append('tax_year', taxYear.value.trim());
  form.append('client_filename', clientFilename.value.trim() || currentFilename || 'client.pdf');
  for (const file of newPdfs.files) {
    form.append('current_year_files', file);
  }

  setStatus(createStatus, 'Creating backup PDF...');
  const response = await fetch('/api/create-backup', { method: 'POST', body: form });
  if (!response.ok) {
    setStatus(createStatus, await response.text(), true);
    return;
  }

  const payload = await response.json();
  createStatus.classList.remove('error');
  createStatus.innerHTML = '';
  const message = document.createElement('span');
  message.textContent = `Created: ${payload.output_path} `;
  const link = document.createElement('a');
  link.href = payload.download_url;
  link.textContent = 'Download PDF';
  link.target = '_blank';
  createStatus.appendChild(message);
  createStatus.appendChild(link);
});

incomeTaxSeason.addEventListener('change', () => {
  syncSeasonFields({ clearResults: true });
  clearActiveDocument();
  setStatus(priorStatus, `Season changed to ${currentSeason()}. Search will use ${sharedYear.value}; final PDF will save under ${taxYear.value}. Open last year's backup again before creating the final PDF.`);
  setStatus(createStatus, '');
});

syncSeasonFields();

closePreview.addEventListener('click', hidePreview);
previewModal.addEventListener('click', (event) => {
  if (event.target.hasAttribute('data-close-preview')) {
    hidePreview();
  }
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !previewModal.hidden) {
    hidePreview();
  }
});
