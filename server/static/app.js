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
var activeCall = -1;

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
  const clickedId = getCallFromElement(evt.target)
  var wasOpen = [];
  $.each(openCalls, function(callId, value) {
    if (value && callId != clickedId) {
      wasOpen.push(callId);
    }
  });
  openCalls[clickedId] = !openCalls[clickedId]
  handleLogEntry(calls[clickedId]) // Refresh the UI.
  $.each(wasOpen, function(idx, callId) {
    openCalls[callId] = false;
    handleLogEntry(calls[callId]);
  });
}

function handleVote(evt) {
  const callId = getCallFromElement(evt.target)
  const transcriptionId = getTranscriptionFromElement(evt.target)
  const vote = $(evt.target).hasClass('upvote') ? 1 : -1
  if (votes[transcriptionId] === vote) {
    return //prevent spam clicking
  }
  votes[transcriptionId] = vote
  $.post(`/api/transcriptions/${transcriptionId}/vote`, {
    vote: vote
  }).done(handleLogEntry).fail(handleApiError)
}

// toggle the 'save' button based on whether the text is unique and long enough
function handleTranscriptionInput(evt) {
  const newTranscription = $(evt.target).val()
  const saveButton = $(evt.target).parent().find('button')

  if (newTranscription.length < 3) {
    saveButton.attr('disabled', true)
    return
  }

  const existingTranscriptions = $(evt.target)
    .parents('.transcriptions')
    .find('.transcription-text')
    .map( function() { return this.textContent} )
    .get()
  const isDuplicate = existingTranscriptions.includes(newTranscription)

  saveButton.attr('disabled', isDuplicate)
}

function handleCustomTranscription(evt) {
  if (evt.preventDefault) { evt.preventDefault() }
  $(evt.target).find('button').attr('disabled', true) // prevent repeat submission
  const callId = getCallFromElement(evt.target)
  const newTranscription = $(evt.target).find('input').val()
  $.post(`/api/calls/${callId}/transcribe`, {
    text: newTranscription
  }).done( (res) => handleLogEntry(res, newTranscription) ).fail(handleApiError)
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
      li.append($('<span class="source-icon" />').append( transcription.source === "user" ? "👤" : "🤖"))
      li.append($('<span class="score" />').text( transcription.upvotes - transcription.downvotes ))
      li.append(getTranscriptionButtons(transcription))
      li.append($('<span class="transcription-text"/>').text(transcription.text))
      tList.append(li)
    })
    callContent.append(tList)

    // The manual transcription entry form
    const customTranscription = $('<div class="custom-entry" />')
    const customForm = $('<form />')
    const customEntry = $('<input type="text" />')
    customEntry.attr('value', obj.transcriptions[0].text)
    customEntry.on('input', handleTranscriptionInput)
    customForm.append($('<button disabled submit>Save</button>'))
    customForm.append(customEntry)
    customTranscription.append(customForm)
    callContent.append(customTranscription)

    const audio = $('<audio controls />')
    audio.attr('src', obj.audio_url);
    callContent.append(audio);

    toggle.addClass('active')
    if (obj._id != activeCall) {
      audio.trigger('play');
    }
    activeCall = obj._id;
  } else {
    callContent.text(obj.transcriptions[0].text)
  }
  logEntry.append(toggle).append(time).append(callContent)
  return logEntry
}

function updateLogEntry(existing, obj) {
  // We assume this is updated in some way or the server wouldn't have sent it,
  // so we don't bother checking to see if there are actually changes.
  // However, we want to avoid clobbering the input and audio elements for
  // already-open entries.
  const t = existing.find('.transcriptions')
  const newEntry = createLogEntry(obj)
  if (t.length > 0) {
    t.replaceWith(newEntry.find('.transcriptions'))
  } else {
    existing.replaceWith(newEntry)
  }
}

function addLogEntry(obj) {
  $('#entries').prepend(createLogEntry(obj))
}

function handleLogEntry(obj, userText) {
  if (userText) {
    const userTranscription = obj.transcriptions.find( t => t.text === userText )
    if (userTranscription) {
      votes[userTranscription._id] = 1;
    }
  }
  calls[obj._id] = obj
  obj.transcriptions.sort(function(a, b) {
    return (b.upvotes - b.downvotes) > (a.upvotes - a.downvotes)
  })
  const existing = $(`#call-${obj._id}`)
  if (existing.length) {
    updateLogEntry(existing.first(), obj)
  } else {
    addLogEntry(obj)
  }

  if (obj.ts > lastTimestamp) { lastTimestamp = obj.ts }
}

function handleApiError(response) {
  const json = response.responseJSON
  if (!json) {
    console.log("Unexpected API Error Response:", response)
    return
  }

  message = json.error
  console.log(`Error: ${message}`);

  $('#alert-box').text(message).fadeIn('fast')
  setTimeout( () => { $('#alert-box').fadeOut('slow') }, 3000)
}
