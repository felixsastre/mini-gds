package availabilitycache

// ErrorKind says how a cached answer disagrees with the host.
type ErrorKind int

const (
	NoError ErrorKind = iota
	OpenWrong
	ClosedWrong
)

func (k ErrorKind) String() string {
	switch k {
	case OpenWrong:
		return "open-wrong (type 1)"
	case ClosedWrong:
		return "closed-wrong (type 2)"
	default:
		return "no error"
	}
}

// Classify compares cached seats with the host's. Only open versus closed counts.
func Classify(cached, host int) ErrorKind {
	switch {
	case cached > 0 && host == 0:
		return OpenWrong
	case cached == 0 && host > 0:
		return ClosedWrong
	default:
		return NoError
	}
}

// closedAtHost is true only when the host answers that the class has no seats. A host that
// cannot answer is no proof that the class is closed.
func closedAtHost(host Host, key Key) bool {
	seats, err := host.Seats(key)
	return err == nil && seats == 0
}

// Wash checks the first top offers against the host and drops the ones the host
// has closed. It returns the offers to show and how many open-wrong errors it caught.
func Wash(offers []Key, top int, host Host) (shown []Key, caught int) {
	for i, offer := range offers {
		if i < top && closedAtHost(host, offer) {
			caught++
			continue
		}
		shown = append(shown, offer)
	}
	return shown, caught
}
