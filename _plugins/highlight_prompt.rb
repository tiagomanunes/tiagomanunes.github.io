require 'cgi'

Jekyll::Hooks.register [:documents], :pre_render do |doc|
  doc.content.gsub!(/```\n(.*?)```/m) do |_match|
    block = $1
    lines = block.lines.map(&:chomp)

    prompt_patterns = [
      /^\$\s+/,
      /^\*Evil-WinRM\* PS .+?>\s+/,
      /^ftp>\s+/,
      /^SQL \(.+\)>\s+/,
      /^PS .+?>\s+/,
      /^smb: .+>\s+/,
      /^sqlite>\s+/,
      /^(\S+?)@(\S+?):(\S+?)[$|#]\s+/
    ]

    result = []
    output_buffer = []

    lines.each do |line|
      matched_prompt = prompt_patterns.find { |regex| line =~ regex }

      if matched_prompt
        # Flush the output buffer first
        unless output_buffer.empty?
          result << "<div>#{CGI.escapeHTML(output_buffer.join("\n"))}</div>"
          output_buffer.clear
        end

        prompt_match = line.match(matched_prompt)
        prompt_str = prompt_match[0]
        command = line.sub(matched_prompt, '')

        result << "<div class=\"cmd-line\"><span class=\"prompt\">#{CGI.escapeHTML(prompt_str)}</span>#{CGI.escapeHTML(command)}</div>"
      else
        output_buffer << line
      end
    end

    # Flush any remaining output
    unless output_buffer.empty?
      result << "<div>#{CGI.escapeHTML(output_buffer.join("\n"))}</div>"
    end

    "<div class=\"terminal-block\">\n#{result.join("\n")}\n</div>"
  end
end
