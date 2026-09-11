/**
 * Theatrical Clock Utility for MiroFish
 * Synchronizes with the backend's 04:53 AM mission start time.
 */

const SESSION_START_REAL = Date.now();
const THEATRICAL_START_SECONDS = (4 * 3600) + (53 * 60); // 04:53:00 AM in seconds

/**
 * Returns a formatted theatrical time string: HH:mm:ss.SSS for "now"
 */
export function getTheatricalTime() {
  return formatToTheatrical(Date.now());
}

/**
 * Converts a real timestamp to a theatrical timestamp string
 */
export function formatToTheatrical(realTimestamp) {
  const dateObj = new Date(realTimestamp);
  const elapsedMs = dateObj.getTime() - SESSION_START_REAL;
  const theatricalSecondsTotal = THEATRICAL_START_SECONDS + (elapsedMs / 1000);
  
  // Wrap around 24h
  const secondsInDay = (theatricalSecondsTotal % 86400);
  
  const hours = Math.floor(secondsInDay / 3600);
  const minutes = Math.floor((secondsInDay % 3600) / 60);
  const seconds = Math.floor(secondsInDay % 60);
  const ms = Math.floor(dateObj.getMilliseconds());
  
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
}

export default {
  getTheatricalTime,
  formatToTheatrical
};
