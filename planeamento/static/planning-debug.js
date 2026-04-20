// Debug helper to fetch planning teams and log them when the team modal is available.
document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('team-modal');
  if (!modal) {
    return;
  }

  // Fetch user/debug info on first load so it shows in Network tab.
  fetch('/api/debug-user', { credentials: 'same-origin' })
    .then((res) => res.json())
    .then((data) => {
      console.log('[debug-user]', data);
    })
    .catch((err) => {
      console.error('[debug-user] fetch failed', err);
    });

  const fetchTeams = () => {
    fetch('/api/planning-teams', { credentials: 'same-origin' })
      .then((res) => res.json())
      .then((data) => {
        console.log('[planning-teams]', data);
      })
      .catch((err) => {
        console.error('[planning-teams] fetch failed', err);
      });
  };

  // Trigger once when the modal is first opened via any click inside day cells.
  const handleClick = (event) => {
    const cell = event.target.closest('.day-cell');
    if (!cell) {
      return;
    }
    fetchTeams();
    document.removeEventListener('click', handleClick);
  };

  document.addEventListener('click', handleClick);
});
