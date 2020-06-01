// const streamEvtSrc = new EventSource('eventsrc')

// in milliseconds
const pollFrequency = 5000
const timeFormat = {
  year: 'numeric', month: 'numeric', day: 'numeric',
  hour: 'numeric', minute: 'numeric', second: 'numeric',
  hour12: false,
  timeZone: 'UTC'
}
const timeFormatter = new Intl.DateTimeFormat('en-US', timeFormat)
let lastTimestamp = 0
let toolboxEle
const calls = {}
const openCalls = {}
const votes = {}

$(function() {
  $('#entries').on('click', '.toggle', handleToggle)
  $('#entries').on('click', '.vote.buttons', handleVote)
  $('#entries').on('submit', handleCustomTranscription)
  var update = function() {
    $.getJSON(`/api/feeds/${pageSettings.feedId}`, {
      since: lastTimestamp,
      limit: 200
    }, function(messages) {
      $.each(messages, function(_idx, message) {
        handleLogEntry(message)
      })
    })
  }
  setInterval(update, pollFrequency)
  update()
})

function getCallFromElement(ele) {
  return $(ele).parents('.call').data('id')
}

function getTranscriptionFromElement(ele) {
  return $(ele).parents('.transcription').data('id')
}

function getTranscriptionButtons(transcription) {
  const container = $('<div class="buttons vote" />')
  const upvote = $('<span class="button upvote">👍</span>')
  const downvote = $('<span class="button downvote">👎</span>')
  if (votes[transcription._id] == 1) {
    upvote.addClass('active')
  } else if (votes[transcription._id] == -1) {
    downvote.addClass('active')
  }
  return container.append(upvote).append(downvote)
}

function handleToggle(evt) {
  const callId = getCallFromElement(evt.target)
  openCalls[callId] = !openCalls[callId]
  handleLogEntry(calls[callId]) // Refresh the UI.
}

function handleVote(evt) {
  const callId = getCallFromElement(evt.target)
  const transcriptionId = getTranscriptionFromElement(evt.target)
  const vote = $(evt.target).hasClass('upvote') ? 1 : -1
  votes[transcriptionId] = vote
  handleLogEntry(calls[callId]) // Refresh the UI.
  $.post(`/api/transcriptions/${transcriptionId}/vote`, {
    vote: vote
  })
}

function handleCustomTranscription(evt) {
  if (evt.preventDefault) { evt.preventDefault() }
  const callId = getCallFromElement(evt.target)
  const newTranscription = $(evt.target).find('input').val()
  $.post(`/api/calls/${callId}/transcribe`, {
    text: newTranscription
  })
}

function createLogEntry(obj) {
  const logEntry = $('<li class="call" />')
  logEntry.attr('id', `call-${obj._id}`)
  logEntry.data('id', obj._id)
  const toggle = $('<div class="buttons button toggle">🔊</div>')
  const time = $('<time />').text(timeFormatter.format(new Date(obj.ts * 1000)))
  const callContent = $('<div class="message" />')
  if (openCalls[obj._id]) {
    // Build up a list of transcriptions and links for them.
    const tList = $('<ul class="transcriptions" />')
    $.each(obj.transcriptions, function(_idx, transcription) {
      const li = $('<li class="transcription" />')
      li.data('id', transcription._id)
      li.append(getTranscriptionButtons(transcription))
      li.append($('<span />').text(transcription.text))
      tList.append(li)
    })

    // The manual transcription entry form
    const customTranscription = $('<li class="custom-entry" />')
    const customForm = $('<form />')
    const customEntry = $('<input type="text" />')
    customEntry.attr('value', obj.transcriptions[0].text)
    customForm.append(customEntry)
    customForm.append($('<button submit>Save</button>'))
    customTranscription.append(customForm)
    tList.append(customTranscription)

    callContent.append(tList)
    toggle.addClass('active')
  } else {
    callContent.text(obj.transcriptions[0].text)
  }
  logEntry.append(toggle).append(time).append(callContent)
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
  calls[obj._id] = obj
  const existing = $(`#call-${obj._id}`)
  if (existing.length) {
    updateLogEntry(existing.first(), obj)
  } else {
    addLogEntry(obj)
  }

  if (obj.ts > lastTimestamp) { lastTimestamp = obj.ts }
}
