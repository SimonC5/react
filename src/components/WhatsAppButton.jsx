function WhatsAppButton() {
  const number = import.meta.env.VITE_WHATSAPP_NUMBER || '573000000000';

  return (
    <a
      href={`https://wa.me/${number}?text=Hola%20SimonC`}
      target="_blank"
      rel="noreferrer"
      aria-label="Contactar por WhatsApp"
      className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500 text-white shadow-lg shadow-emerald-500/30 transition hover:scale-105 hover:bg-emerald-400"
    >
      <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="h-7 w-7">
        <path d="M19.05 4.95A9.9 9.9 0 0 0 3.18 15.7L2.5 21l5.42-1.42a9.9 9.9 0 0 0 11.13-13.63ZM12 18.12c-1.53 0-3.04-.4-4.36-1.15l-.31-.18-3.21.84.86-3.13-.2-.32A8.18 8.18 0 1 1 12 18.12Zm4.49-6.1c-.25-.13-1.48-.73-1.71-.81-.23-.08-.4-.13-.57.13-.17.26-.66.81-.81 1-.15.17-.3.19-.55.06-.25-.13-1.05-.39-2-1.25-.74-.66-1.24-1.48-1.39-1.73-.15-.26-.02-.39.11-.53.12-.12.26-.3.39-.45.13-.15.18-.26.26-.43.08-.17.04-.32-.02-.45-.06-.13-.57-1.38-.78-1.89-.2-.5-.4-.44-.57-.45h-.49c-.17 0-.45.07-.69.32-.24.25-.9.88-.9 2.14 0 1.26.93 2.48 1.05 2.66.13.17 1.82 2.8 4.42 3.92.62.27 1.1.43 1.48.55.62.2 1.19.17 1.64.1.5-.08 1.48-.6 1.69-1.18.21-.58.21-1.08.15-1.18-.06-.1-.23-.17-.49-.3Z" />
      </svg>
    </a>
  );
}

export default WhatsAppButton;
