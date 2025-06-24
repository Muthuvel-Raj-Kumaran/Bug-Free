  const urlParams = new URLSearchParams(window.location.search);
  const fixedGameName = urlParams.get('game_name');

  // Helper to safely parse JSON
  async function safeJson(response) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }

document.getElementById('openModalBtn').addEventListener('click', () => {
  document.getElementById('ticketModal').classList.add('Create-ticket--active'); 
  loadGameNames();
  loadAssignees();

  // Right after loadGameNames() and loadAssignees():
  const projectInput = document.getElementById('project');
  const gameNameInput = document.getElementById('ticketGameName');

  if (projectInput.value.trim()) {
    // Populate from project input on open
    fetch(`/api/get_game_by_project?project=${encodeURIComponent(projectInput.value.trim())}`)
      .then(res => res.json())
      .then(data => gameNameInput.value = data.game_name || projectInput.value.trim())
      .catch(console.error);
  }


  // Reset and enable input fields
  projectInput.disabled = false;
  projectInput.value = '';

  if (fixedGameName) {
    gameSelect.disabled = true;
    gameSelect.value = fixedGameName;
  } else {
    gameSelect.disabled = false;
    gameSelect.value = '';
  }

  projectInput.removeEventListener('input', syncGameName);
  projectInput.addEventListener('input', syncGameName);

  function syncGameName() {
    const projectName = projectInput.value.trim();
    if (!fixedGameName) {
      gameSelect.value = projectName;
    }
  }
});


 
  // === Forms ===
  document.getElementById('ticketForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    for (let [key, value] of formData.entries()) {
      console.log(`${key}: ${value}`);
    }

    const gameName = document.getElementById('ticketGameName').value;
    if (!gameName) {
      alert('Please select a game name.');
      return;
    }

    try {
      const response = await fetch('/submit_ticket', {
        method: 'POST',
        body: formData
      });

      const result = await safeJson(response);
      if (response.ok) {
        form.reset();
        document.getElementById('ticketModal').style.display = 'none';
        loadTickets();
      } else {
        alert('Error: ' + (result?.error || response.statusText));
      }
    } catch (err) {
      alert('Network error: ' + err.message);
    }
  });

  document.getElementById('inviteForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('inviteName').value.trim();
    // const role = document.getElementById('inviteRole').value.trim();
    const email = document.getElementById('inviteEmail').value.trim();

    if (!name ||!email) {
      alert('Please fill all fields.');
      return;
    }

    try {
      const response = await fetch('/invite_user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email })
      });

      const result = await safeJson(response);
      if (response.ok) {
        alert('User invited!');
        document.getElementById('inviteForm').reset();
        document.getElementById('inviteModal').style.display = 'none';
      } else {
        alert('Error: ' + (result?.error || response.statusText));
      }
    } catch (err) {
      alert('Network error: ' + err.message);
    }
  });

  document.getElementById('clearSearchBtn').addEventListener('click', () => {
    document.getElementById('searchInput').value = '';
    document.getElementById('filterType').value = '';
    loadTickets();
  });

  // === Load Tickets ===
  async function loadTickets() {
  console.log('Loading tickets...');
  const workType = document.getElementById('filterType').value;
  const gameName = '';
  const searchText = document.getElementById('searchInput').value.trim();

  console.log({ workType, gameName, searchText });

  let url = '/get_tickets?';
  if (workType) url += `workType=${encodeURIComponent(workType)}&`;
  if (gameName) url += `gameName=${encodeURIComponent(gameName)}&`;
  if (searchText) url += `search=${encodeURIComponent(searchText)}&`;

  console.log('Fetch URL:', url);

  try {
    const response = await fetch(url);
        let tickets = await safeJson(response);
    if (!response.ok) {
      alert('Error loading tickets: ' + (tickets?.error || response.statusText));
      return;
    }

    tickets = applyFilters(tickets);


    if (!response.ok) {
      alert('Error loading tickets: ' + (tickets?.error || response.statusText));
      return;
    }

    console.log('Tickets fetched:', tickets);

    const statuses = ['todo', 'inprocess', 'inreview', 'done', 'onhold', 'suggestion'];
    statuses.forEach(id => {
      const col = document.getElementById(id);
      col.innerHTML = `<h2 class="un-column__header">${col.querySelector('h2').textContent}</h2>`;
    });

    tickets.forEach(ticket => {
      console.log('Rendering ticket:', ticket);
      let colId = ticket.status.toLowerCase().replace(/\s+/g, '');
      if (!statuses.includes(colId)) colId = 'todo';

      const col = document.getElementById(colId);
      if (!col) {
        console.warn(`No column found for status: ${ticket.status} (id: ${colId})`);
        return;
      }
      const ticketDiv = document.createElement('div');
      ticketDiv.classList.add('ticket');
      ticketDiv.textContent = ticket.summary;
      ticketDiv.dataset.ticketId = ticket.id;

      ticketDiv.addEventListener('click', () => showTicketDetails(ticket));
      col.appendChild(ticketDiv);
    });
  } catch (err) {
    alert('Network error: ' + err.message);
  }
}

  // === Ticket Detail Modal ===
  function showTicketDetails(ticket) {
  document.getElementById('ticketDetailModal').classList.remove('hidden');
  document.getElementById('detailSummary').value = ticket.summary || '';
  document.getElementById('detailProject').value = ticket.project || '';
  document.getElementById('detailType').value = ticket.work_type || 'Task';
  document.getElementById('detailStatus').value = ticket.status || 'To Do';
  document.getElementById('detailDescription').value = ticket.description || '';
  document.getElementById('detailTeam').value = ticket.team || '';
  document.getElementById('detailGame').value = ticket.game_name || '';
  document.getElementById('saveTicketBtn').dataset.ticketId = ticket.id;

  if (fixedGameName) {
    document.getElementById('detailGame').disabled = true;
  }

  // Load assignees and select the current assignee
  loadDetailAssignees(ticket.assignee);
  

  // Attachments rendering code stays the same...
  const attachmentsList = document.getElementById('detailAttachmentsList');
  attachmentsList.innerHTML = '';

  if (ticket.attachments?.length) {
    const seen = new Set();
    ticket.attachments.forEach(att => {
      if (seen.has(att.filename)) return;
      seen.add(att.filename);

      const ext = att.filename.split('.').pop().toLowerCase();
      const isImage = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext);

      const itemDiv = document.createElement('div');
      itemDiv.classList.add('attachment-item');
      itemDiv.dataset.attachmentId = att.id;

      if (isImage) {
        const img = document.createElement('img');
        img.src = `/attachment/${att.id}`;
        img.alt = att.filename;
        itemDiv.appendChild(img);
      }

      const link = document.createElement('a');
      link.href = `/attachment/${att.id}`;
      link.textContent = att.filename;
      link.target = '_blank';
      itemDiv.appendChild(link);

      const removeBtn = document.createElement('button');
      removeBtn.textContent = 'Remove';
      removeBtn.classList.add('remove-attachment-btn');
      removeBtn.addEventListener('click', async () => {
        if (confirm(`Remove "${att.filename}"?`)) {
          await removeAttachment(att.id, ticket.id);
        }
      });
      itemDiv.appendChild(removeBtn);

      attachmentsList.appendChild(itemDiv);
    });
  } else {
    attachmentsList.textContent = 'No attachments';
  }
}

  async function loadDetailAssignees(selectedAssignee = '') {
  try {
    const res = await fetch('/active_users');
    const users = await res.json();

    const detailAssignee = document.getElementById('detailAssignee');
    detailAssignee.innerHTML = '<option value="">Select Assignee</option>';

    users.forEach(u => {
      const option = document.createElement('option');
      option.value = u.id;       // Use ID as value
      option.textContent = u.name; // Display name
      detailAssignee.appendChild(option);
    });

    if (selectedAssignee) {
      // selectedAssignee might be id or name, adapt accordingly
      detailAssignee.value = selectedAssignee; // set selected assignee by id
    }
  } catch (err) {
    console.error('Failed to load assignees:', err);
  }
}


  async function removeAttachment(attachmentId, ticketId) {
    try {
      const response = await fetch(`/delete_attachment/${attachmentId}`, { method: 'DELETE' });
      if (!response.ok) throw new Error(await response.text());

      const updated = await fetch(`/get_ticket/${ticketId}`);
      const updatedTicket = await safeJson(updated);

      if (updated.ok) showTicketDetails(updatedTicket);
      else {
        document.getElementById('ticketDetailModal').classList.add('hidden');
        loadTickets();
      }
    } catch (err) {
      alert('Error removing attachment: ' + err.message);
    }
  }

  document.getElementById('saveTicketBtn').addEventListener('click', async () => {
    const ticketId = document.getElementById('saveTicketBtn').dataset.ticketId;
    const fileInput = document.getElementById('newAttachmentInput');

    const payload = {
      summary: document.getElementById('detailSummary').value,
      project: document.getElementById('detailProject').value,
      work_type: document.getElementById('detailType').value,
      status: document.getElementById('detailStatus').value,
      description: document.getElementById('detailDescription').value,
      assignee: document.getElementById('detailAssignee').value,
      team: document.getElementById('detailTeam').value,
      game_name: document.getElementById('detailGame').value,
    };

    try {
      const updateResp = await fetch(`/update_ticket/${ticketId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!updateResp.ok) throw new Error(await updateResp.text());

      if (fileInput.files.length > 0) {
        const formData = new FormData();
        for (let file of fileInput.files) formData.append('attachments', file);

        const attachResp = await fetch(`/upload_attachment/${ticketId}`, {
          method: 'POST',
          body: formData,
        });

        if (!attachResp.ok) {
          const msg = await safeJson(attachResp);
          alert('Attachment upload failed: ' + (msg?.message || attachResp.statusText));
          return;
        }
      }

      loadTickets();
      document.getElementById('ticketDetailModal').classList.add('hidden');
      fileInput.value = '';
    } catch (err) {
      alert('Error updating ticket: ' + err.message);
    }
  });

  // === Load Game Names ===
 async function loadGameNames() {
  const projectInput = document.getElementById('project');
  const gameNameInput = document.getElementById('ticketGameName');

  projectInput.addEventListener('input', () => {
    const pname = projectInput.value.trim();
    if (!fixedGameName) {
      gameNameInput.value = pname; // Sync gameName to project name
    }
  });

}

  // === Filters & Init ===
  document.getElementById('filterType').addEventListener('change', loadTickets);
  document.getElementById('searchInput').addEventListener('input', loadTickets);
  document.getElementById('backToProjectBtn').addEventListener('click', () => {
    window.location.href = '/project?email=' + encodeURIComponent(userEmail);

  });

const ticketDetailModal = document.getElementById('ticketDetailModal');
const closeDetailBtn = document.getElementById('closeDetailBtn');

closeDetailBtn.addEventListener('click', () => {
  ticketDetailModal.classList.add('hidden');
});

const ticketModal = document.getElementById('ticketModal');
const cancelTicketBtn = document.getElementById('cancelTicketBtn');

cancelTicketBtn.addEventListener('click', (e) => {
  e.preventDefault();
  ticketModal.classList.remove('Create-ticket--active');
});


// -------------- invite user

document.addEventListener('DOMContentLoaded', () => {
  // Invite modal handlers
  const openInviteBtn = document.getElementById('openInviteBtn');
  const inviteModal = document.getElementById('inviteModal');
  const inviteCancelBtn = document.getElementById('inviteCancelBtn');

  openInviteBtn?.addEventListener('click', () => {
    inviteModal.classList.add('active');
  });

  inviteCancelBtn?.addEventListener('click', () => {
    inviteModal.classList.remove('active');
  });

  // Back to project button
  const backBtn = document.getElementById('backToProjectBtn');
  backBtn?.addEventListener('click', () => {
    console.log("Back button clicked");
    window.location.href = '/projects';
  });
});

// -------------- Create Ticket
document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('ticketModal');
  const openBtn = document.getElementById('openModalBtn');
  const cancelBtn = document.getElementById('cancelTicketBtn');
  

  openBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    modal.classList.add('Create-ticket--active');
  });

  cancelBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    modal.classList.remove('Create-ticket--active');
  });
});


function loadAssignees() {
  fetch('/active_users')
    .then(res => res.json())
    .then(users => {
      // Fill assignee dropdown in Create Ticket modal
      const createDropdown = document.getElementById('assigneeDropdown');
      createDropdown.innerHTML = '<option value="">Select Assignee</option>';
      // Fill assignee dropdown in Ticket Detail modal
      const detailDropdown = document.getElementById('detailAssignee');
      detailDropdown.innerHTML = '<option value="">Select Assignee</option>';

      users.forEach(u => {
        const option1 = document.createElement('option');
        option1.value = u.id;
        option1.textContent = u.name;
        createDropdown.appendChild(option1);

        const option2 = document.createElement('option');
        option2.value = u.name;  // or use u.id if your ticket stores assignee by ID
        option2.textContent = u.name;
        detailDropdown.appendChild(option2);
      });
    });
}


// Loader

    function showLoader() {
        document.getElementById('loader-overlay').style.display = 'flex';
    }

    function hideLoader() {
        document.getElementById('loader-overlay').style.display = 'none';
    }

    // Attach loader to all form submissions
    document.addEventListener("DOMContentLoaded", function () {
        // On all forms
        document.querySelectorAll("form").forEach(form => {
            form.addEventListener("submit", function () {
                showLoader();
            });
        });

        // On buttons with fetch/ajax
        document.querySelectorAll("button").forEach(button => {
            button.addEventListener("click", function (e) {
                // Optional: detect if button triggers fetch/XHR
                if (button.dataset.loader !== "false") {
                    showLoader();
                    setTimeout(() => {
                        // Just in case it’s not a form and no fetch happens
                        hideLoader();
                    }, 3000); 
                }
            });
        });

        // Automatically hide loader on page load
        window.addEventListener("load", hideLoader);
    });

    // Hook for manual fetch calls
    function fetchWithLoader(url, options) {
        showLoader();
        return fetch(url, options).finally(hideLoader);
    }

    // TeamName Filter

    const searchInput = document.getElementById('searchInput');
    const filterType = document.getElementById('filterType');
    const filterTeam = document.getElementById('filterTeam');

    // Modify your load/display logic or add this where you're filtering tickets
    function applyFilters(tickets) {
      const searchTerm = searchInput.value.trim().toLowerCase();
      const selectedType = filterType.value;
      const selectedTeam = filterTeam.value;

      return tickets.filter(ticket => {
        const matchesSearch = !searchTerm || ticket.summary.toLowerCase().includes(searchTerm);
        const matchesType = !selectedType || ticket.workType === selectedType;
        const matchesTeam = !selectedTeam || ticket.team === selectedTeam;

        return matchesSearch && matchesType && matchesTeam;
      });
    }

    // Add listeners to filters
    filterType.addEventListener('change', loadTickets);
    filterTeam.addEventListener('change', loadTickets);
    searchInput.addEventListener('input', loadTickets);

window.addEventListener('load', () => {
  loadTickets();
  loadGameNames();
});


  