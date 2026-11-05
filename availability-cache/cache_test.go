package availabilitycache_test

import (
	"sync"
	"testing"
	"testing/quick"
	"time"

	ac "availability-cache"
)

func TestClassify(t *testing.T) {
	tests := []struct {
		cached, host int
		want         ac.ErrorKind
	}{
		{4, 0, ac.OpenWrong},
		{0, 4, ac.ClosedWrong},
		{4, 2, ac.NoError},
		{0, 0, ac.NoError},
	}
	for _, tt := range tests {
		if got := ac.Classify(tt.cached, tt.host); got != tt.want {
			t.Errorf("Classify(%d, %d) = %v, want %v", tt.cached, tt.host, got, tt.want)
		}
	}
}

func TestErrorKindString(t *testing.T) {
	want := map[ac.ErrorKind]string{
		ac.NoError:     "no error",
		ac.OpenWrong:   "open-wrong (type 1)",
		ac.ClosedWrong: "closed-wrong (type 2)",
	}
	for kind, s := range want {
		if got := kind.String(); got != s {
			t.Errorf("%d.String() = %q, want %q", kind, got, s)
		}
	}
}

func TestWashWithMoreTopThanOffers(t *testing.T) {
	host := &fakeHost{seats: map[ac.Key]int{{Flight: "AA100", Class: "M"}: 0}}
	offers := []ac.Key{{Flight: "AA100", Class: "M"}}
	shown, caught := ac.Wash(offers, 5, host)
	if len(shown) != 0 || caught != 1 {
		t.Errorf("shown %v, caught %d; want none shown, 1 caught", shown, caught)
	}
}

func TestWashWithZeroTopChecksNothing(t *testing.T) {
	host := &fakeHost{seats: map[ac.Key]int{}}
	offers := []ac.Key{{Flight: "AA100", Class: "M"}}
	shown, caught := ac.Wash(offers, 0, host)
	if len(shown) != 1 || caught != 0 || host.calls != 0 {
		t.Errorf("shown %v, caught %d, calls %d; want 1 shown, 0 caught, 0 calls", shown, caught, host.calls)
	}
}

// Property: whatever the TTL and the age, an entry reaches the host exactly when it has
// expired (age at the TTL or more) or its flight is restricted. This covers the boundary
// and entries that came from the host as well as those pushed by the airline.
func TestHostAskedExactlyWhenExpiredOrRestricted(t *testing.T) {
	prop := func(ttlSeconds, ageSeconds uint16, seats uint8, restricted, fromHost bool) bool {
		ttl := time.Duration(ttlSeconds%600+1) * time.Second
		age := time.Duration(ageSeconds%1200) * time.Second
		key := ac.Key{Flight: "AA100", Class: "M"}

		now := epoch
		host := &fakeHost{seats: map[ac.Key]int{key: 5}}
		c := ac.New(ttl, host, func() time.Time { return now })
		if fromHost {
			c.Availability(key)
			host.calls = 0
		} else {
			c.Update(key, int(seats%10))
		}
		if restricted {
			c.Restrict(key.Flight)
		}
		now = now.Add(age)
		c.Availability(key)

		wantCalls := 0
		if restricted || age >= ttl {
			wantCalls = 1
		}
		return host.calls == wantCalls
	}
	if err := quick.Check(prop, nil); err != nil {
		t.Error(err)
	}
}

// Concurrent readers, updaters and a restrict call must not race (run with -race).
func TestConcurrentUse(t *testing.T) {
	host := &lockedHost{}
	c := ac.New(time.Minute, host, time.Now)
	key := ac.Key{Flight: "AA100", Class: "M"}

	var wg sync.WaitGroup
	for range 20 {
		wg.Add(3)
		go func() { defer wg.Done(); c.Availability(key) }()
		go func() { defer wg.Done(); c.Update(key, 3) }()
		go func() { defer wg.Done(); c.Restrict("AA200") }()
	}
	wg.Wait()
}

// A host that is slow to answer must not hold up requests that need no host call.
func TestSlowHostDoesNotBlockOtherKeys(t *testing.T) {
	host := &blockingHost{asked: make(chan struct{}), release: make(chan struct{})}
	c := ac.New(time.Minute, host, time.Now)
	fresh := ac.Key{Flight: "AA200", Class: "M"}
	c.Update(fresh, 3)

	slow := make(chan int)
	go func() { seats, _ := c.Availability(ac.Key{Flight: "AA100", Class: "M"}); slow <- seats }()
	<-host.asked // the slow request is now waiting for the host

	answered := make(chan int)
	go func() { seats, _ := c.Availability(fresh); answered <- seats }()
	select {
	case seats := <-answered:
		if seats != 3 {
			t.Errorf("fresh entry answered %d seats, want 3", seats)
		}
	case <-time.After(time.Second):
		t.Error("a fresh entry waited for a slow host call on another key")
	}
	close(host.release)
	<-slow
}

// An airline update that arrives while the host is still answering is newer than that
// answer: the late answer must not overwrite it, or a closed class would show as open.
func TestSlowHostAnswerDoesNotOverwriteANewerUpdate(t *testing.T) {
	host := &blockingHost{asked: make(chan struct{}), release: make(chan struct{})}
	c := ac.New(time.Minute, host, time.Now)
	key := ac.Key{Flight: "AA100", Class: "M"}

	answered := make(chan int)
	go func() { seats, _ := c.Availability(key); answered <- seats }()
	<-host.asked // the request is waiting for the host, which will say 5 seats
	c.Update(key, 0)
	close(host.release)
	<-answered

	if seats, _ := c.Availability(key); seats != 0 {
		t.Errorf("availability is %d seats after the airline closed the class, want 0", seats)
	}
}

type blockingHost struct {
	asked   chan struct{}
	release chan struct{}
}

func (h *blockingHost) Seats(ac.Key) (int, error) {
	close(h.asked)
	<-h.release
	return 5, nil
}

type lockedHost struct {
	mu    sync.Mutex
	calls int
}

func (h *lockedHost) Seats(ac.Key) (int, error) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.calls++
	return 5, nil
}

// Property: a class is open exactly while its last message has seats; with no message it is open.
func TestStatusBoardOpenOnlyWhileLastMessageHasSeats(t *testing.T) {
	prop := func(messages []uint8) bool {
		b := ac.NewStatusBoard()
		key := ac.Key{Flight: "AA100", Class: "M"}
		for _, seats := range messages {
			b.Apply(key, int(seats))
		}
		return b.Open(key) == (len(messages) == 0 || messages[len(messages)-1] > 0)
	}
	if err := quick.Check(prop, nil); err != nil {
		t.Error(err)
	}
}
