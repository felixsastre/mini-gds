// Package availabilitycache models a distributor's copy of airline availability:
// entries that expire, updates pushed by the airline, and checks against the host.
package availabilitycache

import (
	"sync"
	"time"
)

// minSweepSize is how many entries the cache holds before it first drops expired ones.
const minSweepSize = 1024

// Key identifies one class on one flight.
type Key struct {
	Flight string
	Class  string
}

// Host is the airline system, the source of truth for seats left.
// It returns an error when it cannot answer, which is not the same as zero seats.
type Host interface {
	Seats(Key) (int, error)
}

type entry struct {
	seats   int
	stored  time.Time
	version uint64 // the value of Cache.writes when the entry was stored
}

// Cache keeps a copy of availability that expires after a time to live.
// It is safe for concurrent use.
type Cache struct {
	ttl  time.Duration
	host Host
	now  func() time.Time

	mu         sync.Mutex
	writes     uint64 // counts every stored entry, so a late host answer can tell it is stale
	entries    map[Key]entry
	sweepAt    int // entries held at which expired ones are next dropped
	restricted map[string]bool
}

// New returns a cache that asks host when an entry is missing or expired.
func New(ttl time.Duration, host Host, now func() time.Time) *Cache {
	return &Cache{
		ttl:        ttl,
		host:       host,
		now:        now,
		entries:    map[Key]entry{},
		sweepAt:    minSweepSize,
		restricted: map[string]bool{},
	}
}

// Availability returns the seats left for key, from the cache when fresh.
// The lock is not held while the host answers, so a slow host delays only the callers
// that need it. Two callers that miss at once both ask the host. If the airline pushes an
// update meanwhile, that update is newer than the host's answer and is kept.
func (c *Cache) Availability(key Key) (int, error) {
	c.mu.Lock()
	e, ok := c.entries[key]
	fresh := ok && !c.restricted[key.Flight] && c.fresh(e)
	asked := c.writes
	c.mu.Unlock()
	if fresh {
		return e.seats, nil
	}

	seats, err := c.host.Seats(key)
	if err != nil {
		return 0, err // an answer the host did not give is not stored
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	if newer, ok := c.entries[key]; ok && newer.version > asked {
		return newer.seats, nil
	}
	c.store(key, seats)
	return seats, nil
}

// fresh reports whether e is younger than the time to live. An entry stored in the future,
// because the clock went back, is not.
func (c *Cache) fresh(e entry) bool {
	age := c.now().Sub(e.stored)
	return age >= 0 && age < c.ttl
}

// Update stores seats for key, as pushed by the airline, and restarts its expiry.
func (c *Cache) Update(key Key, seats int) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.store(key, seats)
}

// store keeps seats for key. The caller holds the lock.
func (c *Cache) store(key Key, seats int) {
	c.writes++
	c.entries[key] = entry{seats: seats, stored: c.now(), version: c.writes}
	if len(c.entries) >= c.sweepAt {
		c.dropExpired()
	}
}

// dropExpired removes the entries past their time to live and sets the next sweep for when
// the cache has doubled, so the cost of a sweep is spread over the writes that filled it.
func (c *Cache) dropExpired() {
	for key, e := range c.entries {
		if !c.fresh(e) {
			delete(c.entries, key)
		}
	}
	c.sweepAt = max(minSweepSize, 2*len(c.entries))
}

// Restrict marks a flight so that every request goes to the host.
func (c *Cache) Restrict(flight string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.restricted[flight] = true
}
