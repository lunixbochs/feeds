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
const calls = {}
const votes = {}
var activeCall = null
let openCall = null

function renderScores() {
  var fixes = parseInt(localStorage.getItem('fixes')) || 0;
  var upvotes = parseInt(localStorage.getItem('upvotes')) || 0;
  var downvotes = parseInt(localStorage.getItem('downvotes')) || 0;
  if (fixes > 0 || upvotes > 0 || downvotes > 0) {
    $("#number-fixes").text(`(${fixes})`);
    $("#number-upvotes").text(`(${upvotes})`);
    $("#number-downvotes").text(`(${downvotes})`);
  }
}

$(function() {
  $('#entries').on('click', '.toggle', handleToggle)
  $('#entries').on('click', '.vote.buttons', handleVote)
  $('#entries').on('submit', handleCustomTranscription)
  var update = function(limit) {
    if (!limit) limit = 200
    $.getJSON(`/api/feeds/${pageSettings.feedId}`, {
      since: lastTimestamp,
      limit: limit
    }, function(messages) {
      // we'll prepend each of these, so process oldest first
      // to maintain overall newest-first order
      messages.sort( (a,b) => a.ts - b.ts )
      $.each(messages, function(_idx, message) {
        handleLogEntry(message)
      })
    })
  }
  setInterval(update, pollFrequency)
  // TODO: instead of re-updating the whole list on load
  // maybe do a synchronous fetch if we need to get more info about a single item we haven't loaded yet
  update(2000)
  renderScores();
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
  if (openCall === clickedId) {
    openCall = null;
  } else {
    const oldOpen = openCall
    openCall = clickedId
    handleLogEntry(calls[oldOpen]) // Close the old one
  }
  handleLogEntry(calls[clickedId]) // Refresh the for the clicked call
}

function handleVote(evt) {
  const callId = getCallFromElement(evt.target)
  const transcriptionId = getTranscriptionFromElement(evt.target)
  const vote = $(evt.target).hasClass('upvote') ? 1 : -1
  if (votes[transcriptionId] === vote) {
    return //prevent spam clicking
  }

  // Count votes
  if (vote === 1) {
    var upvotes = parseInt(localStorage.getItem('upvotes')) || 0;
    window.localStorage.setItem('upvotes', ++upvotes);
  } else {
    var downvotes = parseInt(localStorage.getItem('downvotes')) || 0;
    window.localStorage.setItem('downvotes', ++downvotes);
  }
  renderScores();

  votes[transcriptionId] = vote
  $.post(`/api/transcriptions/${transcriptionId}/vote`, {
    vote: vote
  }).done(handleLogEntry).fail(handleApiError)
}

// toggle the 'save' button based on whether the text is unique and long enough
function handleTranscriptionInput(evt) {
  const newTranscription = $(evt.target).val()
  const saveButton = $(evt.target).parent().find('button')
  evt.target.style.height = evt.target.scrollHeight + 'px'

  if (newTranscription.length < 3) {
    saveButton.attr('disabled', true)
    return
  }

  const callId = getCallFromElement(evt.target)
  const isDuplicate = calls[callId]
    .transcriptions
    .some(function(transcription) {
      return transcription.text === newTranscription
    })

  saveButton.attr('disabled', isDuplicate)
}

function handleTranscriptionInputKeydown(evt) {
  if (evt.which === 13) {
    // The user pressed enter, treat this as a submission and don't pass the
    // newline through.
    if (evt.preventDefault) { evt.preventDefault() }
    $(evt.target).parent().submit()
  }
}

function handleCustomTranscription(evt) {
  if (evt.preventDefault) { evt.preventDefault() }
  $(evt.target).find('button').attr('disabled', true) // prevent repeat submission
  const callId = getCallFromElement(evt.target)
  const newTranscription = $(evt.target).find('textarea').val()

  var fixes = parseInt(localStorage.getItem('fixes')) || 0;
  window.localStorage.setItem('fixes', ++fixes);
  renderScores();

  $.post(`/api/calls/${callId}/transcribe`, {
    text: newTranscription
  }).done( (res) => handleLogEntry(res, newTranscription) ).fail(handleApiError)
}

function handleSpeedButtonClick(evt) {
  const audio = $(evt.target).parent().find('audio');
  const speedButton = $(evt.target).parent().find('input[type="checkbox"]');
  if(speedButton.prop('checked')) { 
    audio[0].playbackRate = 0.5;
  } else {
    audio[0].playbackRate = 1.0;
  }
}


function createLogEntry(obj) {
  const logEntry = $('<li class="call" />')
  logEntry.attr('id', `call-${obj._id}`)
  logEntry.data('id', obj._id)
  const toggle = $('<div class="buttons button toggle">🔊</div>')
  const time = $('<time />').text(timeFormatter.format(new Date(obj.ts * 1000)).replace(', ', ' '))
  const callContent = $('<div class="message" />')
  if (openCall === obj._id) {
    // Build up a list of transcriptions and links for them.
    const tList = $('<ul class="transcriptions" />')
    $.each(obj.transcriptions, function(_idx, transcription) {
      const li = $('<li class="transcription" />')
      li.data('id', transcription._id)
      li.append(getTranscriptionButtons(transcription))
      li.append($('<span class="score" />').text(`(${transcription.upvotes - transcription.downvotes})`))
      li.append($('<span class="source-icon" />').append( transcription.source === "user" ? "👤" : "🤖"))
      li.append($('<span class="transcription-text"/>').text(transcription.text))
      tList.append(li)
    })
    callContent.append(tList)

    // The manual transcription entry form
    const customTranscription = $('<div class="custom-entry" />')
    const customForm = $('<form />')
    const customEntry = $('<textarea wrap="soft" rows="2" />')
    customEntry.text(obj.transcriptions[0].text)
    customEntry.on('input', handleTranscriptionInput)
    // We use keyup (exclusively) to catch pressing enter. We can't use it for
    // our general input handler because that wouldn't catch certain mouse
    // actions, etc.
    customEntry.on('keydown', handleTranscriptionInputKeydown)
    customForm.append($('<button disabled submit>Save</button>'))
    customForm.append(customEntry)
    customTranscription.append(customForm)
    callContent.append(customTranscription)

    const audio = $('<audio controls />')
    audio.attr('src', obj.audio_url);
    callContent.append(audio);

    const speedButton = $('<input type="checkbox" />');
    speedButton.on('click', handleSpeedButtonClick);
    callContent.append(speedButton);
    callContent.append($('<label>0.5x speed</label>'));

    toggle.addClass('active')
    if (obj._id != activeCall) {
      audio.trigger('play');
    }
    activeCall = obj._id;
    logEntry.append(toggle).append(callContent)
  } else {
    let transcription = obj.transcriptions[0];
    callContent.append($('<span class="score" />').text(`(${transcription.upvotes - transcription.downvotes})`))
    callContent.append($('<span class="source-icon" />').append(transcription.source === "user" ? "👤" : "🤖"))
    callContent.append($('<span class="transcription-text" />').text(transcription.text));
    logEntry.append(toggle).append(time).append(callContent)
  }
  return logEntry
}

function updateLogEntry(existing, obj) {
  // We assume this is updated in some way or the server wouldn't have sent it,
  // so we don't bother checking to see if there are actually changes.
  // However, we want to avoid clobbering the input and audio elements for
  // already-open entries... unless we're closing the entry.
  const t = existing.find('.transcriptions')
  const newEntry = createLogEntry(obj)
  if (t.length > 0 && openCall === obj._id) {
    t.replaceWith(newEntry.find('.transcriptions'))
  } else {
    existing.replaceWith(newEntry)
  }
}

function addLogEntry(obj) {
  $('#entries').prepend(createLogEntry(obj))
}

function handleLogEntry(obj, userText) {
  if (!obj) { return }
  if (userText) {
    const userTranscription = obj.transcriptions.find( t => t.text === userText )
    if (userTranscription) {
      votes[userTranscription._id] = 1;
    }
  }
  calls[obj._id] = obj
  obj.transcriptions.sort(function(a, b) {
    const diff = (b.upvotes - b.downvotes) - (a.upvotes - a.downvotes)
    if (diff == 0) {
      if (a._id < b._id) { return -1 }
      return 1
    }
    return diff
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
