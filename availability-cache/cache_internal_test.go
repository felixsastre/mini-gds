package availabilitycache

import (
	"fmt"
	"testing"
	"time"
)

// Entries nobody asks for again must not pile up: once the map has grown, a write drops
// the ones that have expired.
func TestExpiredEntriesAreDroppedAsTheCacheGrows(t *testing.T) {
	now := time.Date(2026, 1, 1, 12, 0, 0, 0, time.UTC)
	c := New(time.Minute, nil, func() time.Time { return now })
	store := func(from, to int) {
		for i := from; i < to; i++ {
			c.Update(Key{Flight: fmt.Sprintf("AA%d", i), Class: "M"}, 3)
		}
	}

	store(0, minSweepSize)
	now = now.Add(2 * time.Minute) // every entry so far has expired
	store(minSweepSize, 2*minSweepSize)

	if got := len(c.entries); got > minSweepSize+1 {
		t.Errorf("%d entries held, want the expired ones dropped (at most %d)", got, minSweepSize+1)
	}
}

func TestFreshEntriesSurviveTheSweep(t *testing.T) {
	now := time.Date(2026, 1, 1, 12, 0, 0, 0, time.UTC)
	c := New(time.Minute, nil, func() time.Time { return now })
	keep := Key{Flight: "KEEP", Class: "M"}
	for i := 0; i < 3*minSweepSize; i++ {
		c.Update(Key{Flight: fmt.Sprintf("AA%d", i), Class: "M"}, 3)
		c.Update(keep, 5) // refreshed all along
	}
	if _, ok := c.entries[keep]; !ok {
		t.Error("a fresh entry was dropped by the sweep")
	}
}
