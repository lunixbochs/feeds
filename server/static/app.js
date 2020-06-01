// const streamEvtSrc = new EventSource('eventsrc')

// in milliseconds
const pollFrequency = 1000
const timeFormat = {
  year: 'numeric', month: 'numeric', day: 'numeric',
  hour: 'numeric', minute: 'numeric', second: 'numeric',
  hour12: false,
  timeZone: 'UTC'
}
const timeFormatter = new Intl.DateTimeFormat('en-US', timeFormat)
let lastTimestamp = 0

$(function() {
  const feedId = $('#entries').first().data('feed')
  setInterval(function() {
    $.getJSON(`/api/feeds/${feedId}`, {
      since: lastTimestamp,
      limit: 100
    }, function(messages) {
      $.each(messages, function(_idx, message) {
        handleLogEntry(message)
      })
    })
  }, pollFrequency)
})

function createLogEntry(obj) {
  const logEntry = $('<li />')
  logEntry.attr('id', `msg${obj._id}`)
  const time = $('<time />').text(timeFormatter.format(new Date(obj.ts * 1000)))
  const msg = $('<span class="message" />').text(obj.transcriptions[0].text)
  logEntry.append(time).append(msg)
  return logEntry
}

function updateLogEntry(existing, obj) {
  // We assume this is updated in some way or the server wouldn't have sent it,
  // so we don't bother checking to see if there are actually changes.
  existing.replaceWith(createLogEntry(obj))
}

function addLogEntry(obj) {
  $('#entries').prepend(createLogEntry(obj))
}

function handleLogEntry(obj) {
  const existing = $(`#msg${obj._id}`)
  if (existing.length) {
    updateLogEntry(existing.first(), obj)
  } else {
    addLogEntry(obj)
  }

  if (obj.ts > lastTimestamp) { lastTimestamp = obj.ts }
}
