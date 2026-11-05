package availabilitycache

import "sync"

// StatusBoard holds what the airline has said through status messages.
// It is safe for concurrent use.
type StatusBoard struct {
	mu    sync.Mutex
	seats map[Key]int
}

// NewStatusBoard returns a board with no messages.
func NewStatusBoard() *StatusBoard {
	return &StatusBoard{seats: map[Key]int{}}
}

// Apply records a status message of seats for key, replacing any earlier one.
func (b *StatusBoard) Apply(key Key, seats int) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.seats[key] = seats
}

// Open reports whether key is open. A class with no message is considered open.
func (b *StatusBoard) Open(key Key) bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	seats, ok := b.seats[key]
	return !ok || seats > 0
}
